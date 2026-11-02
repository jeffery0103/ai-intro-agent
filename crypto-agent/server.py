"""部署在 Render 的服務。
- GET/HEAD /:UptimeRobot 每 5 分鐘戳一次,讓免費方案不休眠;順便當時鐘——過了台灣 08:30 還沒發今天的報告就發。
- POST /tg:Telegram webhook,處理指令與設定 Agent 的追問。
環境變數:GEMINI_API_KEY、TELEGRAM_BOT_TOKEN、GIST_ID、GITHUB_TOKEN(都由使用者在 Render 後台設定)。
用法(本機測試):python server.py"""
import datetime as dt, hashlib, json, os, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import storage, report, sim, profile_agent, tg

PORT = int(os.environ.get("PORT", 8080))
SECRET = hashlib.sha256((tg.TOKEN or "local").encode()).hexdigest()[:32]   # webhook 驗證碼,由 token 推出來,不用另外設
RETRY_MIN = 30
job_lock, bot_lock = threading.Lock(), threading.Lock()
HELP = ("我是加密貨幣每日報告 Agent(模擬資金、學習用途)。每天台灣時間 08:30 後會自動發報告。\n\n"
        "/report 今天的報告\n/status 模擬帳戶\n/terms 名詞小教室\n/setup 重新設定本金、虧損上限、幣種\n"
        "/resume 觸發虧損上限後,檢討完要繼續\n/cancel 取消設定")


def log(*a):
    print(dt.datetime.now().strftime("%m-%d %H:%M:%S"), *a, flush=True)


def bot():
    return storage.load("bot.json") or {}


def expected_date(now=None):
    """現在應該要有的最新報告日期:台灣 08:30(UTC 00:30)後是 UTC 昨天,之前是前天。"""
    now = now or dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(minutes=30, days=1)).strftime("%Y-%m-%d")


def due(b):
    if not b.get("chat_id") or b.get("setup") or not storage.load("profile.json"):
        return False
    if b.get("last_report", "") >= expected_date():
        return False
    last = b.get("last_attempt")
    return not last or dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last) > dt.timedelta(minutes=RETRY_MIN)


def daily_job(force=False):
    """產生並推送報告。同一時間只跑一個。"""
    if not job_lock.acquire(blocking=False):
        return
    try:
        with bot_lock:
            b = bot(); b["last_attempt"] = dt.datetime.now(dt.timezone.utc).isoformat(); storage.save("bot.json", b)
        r = report.run()
        if r is None:
            return
        with bot_lock:
            b = bot()
            if force or r["date"] != b.get("last_report"):
                tg.send(b["chat_id"], r["chat"])
            b["last_report"] = r["date"]; storage.save("bot.json", b)
        log("報告", r["date"], "稽查", "通過" if r["ok"] else "未通過", "|", " / ".join(f"{x['步驟']} {x['秒']}s" for x in report.trace))
    except Exception:
        log("報告失敗\n" + traceback.format_exc())
    finally:
        job_lock.release()


def status_text():
    L = sim.load()
    if not L:
        return "模擬帳戶還沒開始,第一份報告發出後就會建立。"
    s = sim.summary(L)
    trades = "\n".join(f"  {t['date']} {t['sym']} {t['side']} @ {round(t['price'], 2)}" for t in L["trades"][-5:]) or "  (還沒有)"
    return (f"💼 模擬帳戶(開始於 {s['開始日']},已跑 {s['已跑天數']} 天)\n"
            f"本金 {s['本金USDT']} → 現在 {s['目前總值USDT']} USDT({s['損益%']:+}%)\n"
            f"對照組(第一天買進不動):{s['對照組(第一天買進不動)總值USDT']} USDT({s['對照組損益%']:+}%)\n"
            f"各幣:{'、'.join(f'{k} {v}' for k, v in s['各幣狀態'].items())}\n"
            f"暫停:{s['是否暫停']}\n最近交易:\n{trades}")


def handle(chat_id, text):
    text = (text or "").strip()
    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else None
    with bot_lock:
        b = bot()
        owner = int(os.environ.get("OWNER_CHAT_ID") or b.get("chat_id") or 0)
        if not owner:
            if cmd != "/start":
                tg.send(chat_id, "傳 /start 開始。"); return
            b["chat_id"] = owner = chat_id; storage.save("bot.json", b)
            log("已登記使用者")
        if chat_id != owner:
            tg.send(chat_id, "這是私人 bot。"); return
        b.setdefault("chat_id", owner)

        if cmd in ("/start", "/help"):
            tg.send(chat_id, HELP)
            if cmd == "/start" and not storage.load("profile.json"):
                cmd = "/setup"
            else:
                return
        if cmd == "/setup":
            b["setup"] = {"prof": profile_agent.new(), "msg": ""}; storage.save("bot.json", b)
            tg.send(chat_id, "開始設定(隨時可以傳 /cancel 取消)。\n\n" + profile_agent.question(b["setup"]["prof"])); return
        if cmd == "/cancel":
            b.pop("setup", None); storage.save("bot.json", b); tg.send(chat_id, "已取消設定。"); return
        if cmd == "/status":
            tg.send(chat_id, status_text()); return
        if cmd == "/terms":
            tg.send(chat_id, report.terms()); return
        if cmd == "/resume":
            ref = sim.resume()
            tg.send(chat_id, "目前沒有暫停。" if ref is None else f"已解除暫停。之後的虧損上限從目前總值 {round(ref)} USDT 重新起算。"); return
        if cmd == "/report":
            latest = storage.load("latest_report.json")
            if latest and latest["date"] >= expected_date():
                tg.send(chat_id, latest["chat"]); return
            tg.send(chat_id, "產生中,大約 10~30 秒⋯")
            threading.Thread(target=daily_job, kwargs={"force": True}).start(); return
        if cmd:
            tg.send(chat_id, "看不懂這個指令。\n\n" + HELP); return

        if b.get("setup"):                       # 設定 Agent 的追問
            st = b["setup"]
            msg, _ = profile_agent.answer(st["prof"], text)
            q = profile_agent.question(st["prof"], msg)
            if q:
                st["msg"] = msg; storage.save("bot.json", b); tg.send(chat_id, q); return
            b.pop("setup"); storage.save("bot.json", b)
            tg.send(chat_id, "整理中⋯")
            tg.send(chat_id, profile_agent.finish(st["prof"]) + "\n\n傳 /report 看今天的報告。"); return
        tg.send(chat_id, "我只看得懂指令喔。\n\n" + HELP)


class H(BaseHTTPRequestHandler):
    def _ok(self, body=b"ok"):
        self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if due(bot()):
            threading.Thread(target=daily_job).start()
        self._ok()

    def do_POST(self):
        if self.path != "/tg" or self.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
            self.send_response(403); self.end_headers(); return
        upd = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        self._ok()                               # 先回 200,Telegram 才不會重送
        m = upd.get("message") or {}
        if m.get("chat", {}).get("id") and "text" in m:
            threading.Thread(target=self._safe, args=(m["chat"]["id"], m["text"])).start()

    @staticmethod
    def _safe(chat_id, text):
        t = time.time()
        try:
            tg.typing(chat_id)
            handle(chat_id, text)
            log(f"訊息處理 {round(time.time() - t, 1)} 秒:{text[:20] if text.startswith('/') else '(回答)'}")
        except Exception:
            log("處理訊息失敗\n" + traceback.format_exc())
            tg.send(chat_id, "出了點問題,請稍後再試。")

    def log_message(self, *a):                   # 不印每個請求,Render 紀錄比較乾淨
        pass


if __name__ == "__main__":
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if tg.TOKEN and url:
        r = tg.set_webhook(url + "/tg", SECRET)
        log("設定 webhook:", "成功" if r.get("ok") else f"失敗 {r.get('error')} {r.get('description')}")
    log("啟動,port", PORT, "| 儲存:", "Gist" if storage.GIST else "本機")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
