"""每日報告:讀設定 → 抓資料 → 算指標 → 推進模擬帳戶 → LLM 寫報告 → 程式核對數字 → LLM 稽查
→ 沒過就退回重寫一次 → 存到 reports/ 與儲存層。每一步都記 Tracing。
用法:python report.py(server.py 也會呼叫 run())"""
import io, json, os, re, sys, time
import gem, market, sim, backtest, storage

WRITER = ["gemini-flash-lite-latest", "gemini-flash-latest"]
AUDITOR = ["gemini-flash-latest", "gemini-flash-lite-latest"]
OUT = os.path.join(market.HERE, "reports")

# 名詞解釋由人工確認後寫死,報告最後原文附上,不讓 LLM 自己解釋(避免講錯)
GLOSSARY = {
    "均線": "過去 N 天收盤價的平均。50 日均線就是最近 50 天的平均價,用來看「最近一段時間大概的價位」。",
    "規則訊號": "這個 Agent 用的固定規則:收盤價在 50 日均線上方就「持有」,下方就「空手」(不持有、拿著現金)。它不是預測,只是跟著趨勢走:漲上去才進場,跌下來就出場。",
    "RSI": "相對強弱指標,0~100。看最近 14 天漲的力道和跌的力道誰大。低於 30 常被說「跌過頭(超賣)」,高於 70「漲過頭(超買)」,但跌過頭之後還可以再跌,不能單獨拿來決定買賣。",
    "波動": "價格每天平均上下跳多少 %。數字越大,一天之內賺或賠的幅度都越大。",
    "回撤": "從最高點往下跌了多少 %。最大回撤就是期間內最慘的那一次,代表「如果你在最高點買,最多會看到帳面虧多少」。",
    "手續費": "每次買或賣都要付的成本,這裡用 0.1%。換手越頻繁,手續費吃掉越多。",
    "樣本外驗證": "只用舊資料挑規則參數,再拿規則沒看過的新資料測試。如果只在舊資料表現好,新資料就不行,代表規則只是剛好背熟了過去(過度擬合)。",
}

WSYS = ("你是加密貨幣新手的每日報告助理,讀者完全不懂投資。只能使用提供的 JSON,不可編造任何數字、新聞或理由。"
        "不可預測價格會漲或跌,不可用『保證』『一定』『必漲』『必跌』『建議買進/賣出』等字眼。"
        "規則訊號要說清楚:這是機械規則、不是預測;並用 JSON 的「訊號理由」「要翻成另一個訊號」解釋為什麼是現在這個訊號、要發生什麼才會改變。"
        "提到 RSI、均線、回撤時用一句白話帶過(讀者看得懂就好),數字照 JSON 寫,不要自己換算新的數字。"
        "寫法:稱呼讀者一律用『你』,不要說『使用者』;像跟朋友解釋,每個幣先用一句話講『這對讀者代表什麼』(例如:規則現在是拿著現金觀望,今天不用做任何事),"
        "再挑 2~3 個最重要的數字說明;不要把 JSON 欄位名稱直接念成句子,也不要每個數字都列。"
        "模擬帳戶要講白話的比較:規則跟對照組誰目前比較好、差多少(用 JSON 的損益%)。"
        "用繁體中文,400 字內,分段:\n## 一句話\n## 各幣狀況(每個幣一小段)\n## 你的模擬帳戶(跟對照組比)\n## 風險提醒(要提到使用者的虧損上限與歷史機率)\n"
        "不用寫名詞解釋和免責聲明,程式會附上。")
ASYS = ("你是稽查員,檢查一份給新手的加密貨幣報告能不能發送。逐條檢查:(1) 報告裡每個數字都要在 JSON 找得到;"
        "(2) 不可有價格預測或『保證/一定/必漲/必跌/建議買進/建議賣出』;(3) 每個幣的規則訊號與 JSON 相符;"
        "(4) 模擬帳戶損益與對照組的比較方向正確(誰比較高);(5) 不可編造 JSON 沒有的資訊(新聞、原因、事件);"
        "(6) 風險提醒有提到使用者的虧損上限。"
        '只輸出 JSON:{"pass": true 或 false, "issues": ["具體問題", ...]}')

trace = []


def step(name, fn):
    t = time.time(); r = fn()
    tries = r.pop("_tries", None) if isinstance(r, dict) else None
    row = {"步驟": name, "秒": round(time.time() - t, 1)}
    if isinstance(r, dict) and ("in" in r or "error" in r):
        row.update({"in": r.get("in"), "out": r.get("out"), "think": r.get("think"), "model": r.get("model") or r.get("error")})
    if tries:
        row["tries"] = " → ".join(f"{x['model'].replace('gemini-','')} {x['error'] or 'OK'} {x['sec']}s" for x in tries)
    trace.append(row)
    return r


def llm(models, prompt, system, **kw):
    log = []
    r = gem.call(models, prompt, system, log=log, **kw)
    r["_tries"] = log
    return r


def numbers_ok(text, facts):
    """程式核對:報告裡 2 位數以上的數字,都要能在 JSON 裡找到(容許四捨五入到整數或 1 位小數)。"""
    allowed = set()
    for tok in re.findall(r"\d+(?:\.\d+)?", json.dumps(facts, ensure_ascii=False).replace(",", "")):
        v = float(tok)
        allowed |= {tok, f"{v:g}", str(round(v)), f"{round(v, 1):g}", f"{round(v, 2):g}"}
    bad = []
    for tok in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        t = tok.replace(",", "")
        if len(t.replace(".", "")) >= 2 and t not in allowed and f"{float(t):g}" not in allowed:
            bad.append(tok)
    return sorted(set(bad))


def safe_funding(s):
    try:
        return market.funding(s)
    except Exception:               # 合約 API 在某些地區連不上,資金費率只是參考,缺了就算了
        return None


def run():
    """產生今天的報告。回傳 {"date", "md"(完整), "chat"(Telegram 用), "ok"};還沒設定回傳 None。"""
    prof = storage.load("profile.json")
    if not prof:
        return None
    trace.clear()
    syms = prof["symbols"]

    rows = step("1 抓日線(Binance 公開 API)", lambda: {s: market.load(s) for s in syms})
    fund = step("1b 抓資金費率", lambda: {s: safe_funding(s) for s in syms})
    L, new = step("2 推進模擬帳戶(程式)", lambda: sim.update(prof, rows))
    bt = step("3 回測與虧損上限對照(程式)", lambda: {s: backtest.analyze(s, prof["max_loss_pct"] / 100) for s in syms})

    facts = {"使用者設定": {"本金USDT": round(prof["capital_usdt"]), "虧損上限%": prof["max_loss_pct"], "幣種": syms},
             "各幣": [], "模擬帳戶": sim.summary(L),
             "今天新交易": [f"{t['sym']} {t['side']} @ {round(t['price'], 2)}" for t in new] or "無"}
    for s in syms:
        snap = market.snapshot(s, rows[s], L["ma"])
        snap["資金費率%(最近3期平均)"] = fund[s]
        b = bt[s]
        snap["回測"] = {"樣本外測試期": b["測試期"],
                      "測試期50日均線規則": b["測試期各均線"][50], "測試期買進持有": b["測試期買進持有"],
                      f"一年內虧到{prof['max_loss_pct']:g}%的機率%": {"50日均線規則": b["一年內虧到上限的機率%"]["50日均線"],
                                                               "買進持有": b["一年內虧到上限的機率%"]["買進持有"]}}
        facts["各幣"].append(snap)
    date = facts["各幣"][0]["日期"]
    payload = json.dumps(facts, ensure_ascii=False, indent=1)

    rep = step("4 寫報告(LLM)", lambda: llm(WRITER, "今日 JSON:\n" + payload, WSYS))
    text = rep.get("text", "(寫報告失敗)")
    bad = step("5 程式核對數字", lambda: numbers_ok(text, facts))

    def audit(t):
        r = llm(AUDITOR, "JSON:\n" + payload + "\n\n報告:\n" + t, ASYS, temperature=0, thinking="low", tries=2, timeout=30)
        try:
            r["verdict"] = gem.parse_json(r["text"])
        except Exception:
            r["verdict"] = {"pass": False, "issues": ["稽查回覆無法解析或稽查失敗"]}
        return r
    aud = step("6 稽查(LLM)", lambda: audit(text))
    first = {"report": text, "numbers": bad, "audit": aud["verdict"]}
    retried = False
    if bad or not aud["verdict"].get("pass"):
        retried = True
        fb = "上一版被退回,問題:\n- " + "\n- ".join(aud["verdict"].get("issues", []) + [f"JSON 找不到的數字:{x}" for x in bad])
        rep = step("7 退回重寫(LLM)", lambda: llm(WRITER, "今日 JSON:\n" + payload + "\n\n" + fb + "\n請修正後重寫整份報告。", WSYS))
        text = rep.get("text", text)
        bad = step("8 程式再核對", lambda: numbers_ok(text, facts))
        aud = step("9 再稽查(LLM)", lambda: audit(text))
    ok = not bad and aud["verdict"].get("pass")

    os.makedirs(OUT, exist_ok=True)
    md = io.StringIO()
    md.write(f"# 加密貨幣每日報告 {date}\n\n")
    if not ok:
        md.write("> ⚠️ 這份報告沒有通過稽查,下面的文字可能有錯,請以「數據」區塊為準。\n\n")
    if L["halted"]:
        md.write(f"> ⛔ 模擬帳戶已在 {L['halted']['date']} 觸發你設定的 {prof['max_loss_pct']:g}% 虧損上限,已全部賣出並暫停。檢討完要繼續,在 Telegram 傳 /resume(或執行 `python sim.py --resume`)。\n\n")
    md.write(text.strip() + "\n\n## 名詞小教室\n")
    for k, v in GLOSSARY.items():
        md.write(f"- **{k}**:{v}\n")
    md.write("\n本報告為學習用途,訊號來自固定規則而非預測,不構成投資建議;是否交易由使用者自行決定。\n\n")
    md.write(f"---\n## 稽查\n- 程式核對數字:{'通過' if not bad else '找不到 ' + '、'.join(bad)}\n- LLM 稽查:`{json.dumps(aud['verdict'], ensure_ascii=False)}`\n")
    if retried:
        md.write(f"- 第一版被退回:數字 {first['numbers'] or '無問題'};稽查 `{json.dumps(first['audit'], ensure_ascii=False)}`\n")
    md.write(f"\n## 數據(程式計算)\n```json\n{payload}\n```\n\n## Tracing\n| 步驟 | 秒 | 輸入 tokens | 輸出 tokens | 思考 tokens | 實際模型 | 嘗試紀錄 |\n|---|---|---|---|---|---|---|\n")
    for t in trace:
        md.write(f"| {t['步驟']} | {t['秒']} | {t.get('in') or '-'} | {t.get('out') or '-'} | {t.get('think') or '-'} | {t.get('model') or '-'} | {t.get('tries') or '-'} |\n")
    md.write(f"| **合計** | {round(sum(t['秒'] for t in trace), 1)} | | | | | |\n")
    for name in (f"{date}.md", "latest.md"):
        io.open(os.path.join(OUT, name), "w", encoding="utf-8").write(md.getvalue())

    chat = f"📊 加密貨幣每日報告 {date}\n\n"
    if not ok:
        chat += "⚠️ 這份報告沒有通過稽查,文字可能有錯。\n\n"
    if L["halted"]:
        chat += f"⛔ 模擬帳戶已在 {L['halted']['date']} 觸發 {prof['max_loss_pct']:g}% 虧損上限,已全部賣出並暫停。檢討完要繼續就傳 /resume。\n\n"
    chat += re.sub(r"^#+\s*(.+)$", r"【\1】", text.strip(), flags=re.M).replace("**", "")
    chat += (f"\n\n稽查:{'通過' if ok else '未通過'}{'(第一版被退回重寫)' if retried else ''}"
             f" · 用時 {round(sum(t['秒'] for t in trace), 1)} 秒\n"
             "名詞看不懂 → /terms   帳戶 → /status\n學習用途,訊號來自固定規則而非預測,不構成投資建議。")
    result = {"date": date, "md": md.getvalue(), "chat": chat, "ok": bool(ok)}
    storage.save("latest_report.json", result)
    return result


def terms():
    return "📖 名詞小教室\n\n" + "\n\n".join(f"【{k}】{v}" for k, v in GLOSSARY.items())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = run()
    if r is None:
        print("還沒有設定,先執行:python profile_agent.py"); sys.exit(1)
    print(r["md"])
