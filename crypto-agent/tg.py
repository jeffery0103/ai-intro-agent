"""Telegram Bot API。token 只從環境變數 TELEGRAM_BOT_TOKEN 讀;沒設定時訊息只印在終端機(本機測試用)。
錯誤訊息只記錯誤種類,不記網址(網址裡有 token)。"""
import json, os, urllib.request, urllib.error

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
sent = []            # 本機測試時記下送出的訊息


def api(method, **params):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=json.dumps(params).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.code, "description": json.loads(e.read() or b"{}").get("description")}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


def send(chat_id, text):
    """超過 Telegram 單則上限(4096 字)就依段落切開。"""
    parts, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) + 2 > 3900 and cur:
            parts.append(cur); cur = ""
        cur += ("\n\n" if cur else "") + para
    parts.append(cur)
    for p in parts:
        if not TOKEN:
            sent.append((chat_id, p)); print(f"[Telegram → {chat_id}]\n{p}\n", flush=True)
            continue
        r = api("sendMessage", chat_id=chat_id, text=p, disable_web_page_preview=True)
        if not r.get("ok"):
            print("Telegram 傳送失敗:", r.get("error"), r.get("description"), flush=True)


def set_webhook(url, secret):
    return api("setWebhook", url=url, secret_token=secret, allowed_updates=["message"], drop_pending_updates=True)


def typing(chat_id):
    """顯示「正在輸入⋯」(約 5 秒),讓使用者知道有在處理。"""
    if TOKEN:
        api("sendChatAction", chat_id=chat_id, action="typing")
