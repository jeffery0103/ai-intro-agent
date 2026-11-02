"""Binance 公開 API 抓日線(不需要金鑰),存到 data/ 當快取;指標全部用程式算,不用 LLM。"""
import json, os, time, urllib.request, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SUPPORTED = {"BTC": "比特幣", "ETH": "以太幣", "SOL": "Solana", "BNB": "幣安幣", "XRP": "瑞波幣"}
START = "2018-01-01"


SPOT_HOSTS = ["https://api.binance.com", "https://data-api.binance.vision"]   # 主站被地區封鎖時改用公開資料站


def _get(url):
    return json.load(urllib.request.urlopen(url, timeout=20))


def _spot(path):
    err = None
    for h in SPOT_HOSTS:
        try:
            return _get(h + path)
        except Exception as e:
            err = e
    raise err


def day(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def load(sym):
    """回傳 [(日期, 收盤價), ...],只含已收盤的日線(UTC 0 點 = 台灣 8 點收盤)。"""
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, f"{sym}USDT_1d.json")
    rows = json.load(open(path)) if os.path.exists(path) else []
    start = rows[-1][0] + 86400000 if rows else int(dt.datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    now = int(time.time() * 1000)
    while start < now:
        k = _spot(f"/api/v3/klines?symbol={sym}USDT&interval=1d&startTime={start}&limit=1000")
        k = [x for x in k if x[6] < now]           # x[6] = 收盤時間,還沒收盤的今天不要
        if not k:
            break
        rows += [[x[0], float(x[4]), float(x[5])] for x in k]
        start = k[-1][0] + 86400000
    json.dump(rows, open(path, "w"))
    return [(day(r[0]), r[1]) for r in rows]


def funding(sym):
    f = _get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}USDT&limit=3")
    return round(sum(float(x["fundingRate"]) for x in f) / len(f) * 100, 4)


def ma(c, i, n):
    return sum(c[i - n + 1:i + 1]) / n


def rsi(c, i, n=14):
    g = l = 0.0
    for j in range(i - n + 1, i + 1):
        ch = c[j] - c[j - 1]
        g += max(ch, 0); l += max(-ch, 0)
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def signal(c, i, n):
    """規則:收盤價在 n 日均線上方 → 持有(1),否則空手(0)。"""
    return 1 if c[i] > ma(c, i, n) else 0


def px(v):
    """價格顯示:1000 以上取整數,以下留 2 位小數。"""
    return round(v) if v >= 1000 else round(v, 2)


def snapshot(sym, rows, n):
    """今天(最後一根已收盤日線)的所有數字,給報告用。"""
    d = [r[0] for r in rows]; c = [r[1] for r in rows]; i = len(c) - 1
    m = ma(c, i, n)
    sig = [signal(c, j, n) for j in range(i - 365, i + 1)]
    changed = next((d[i - 365 + j] for j in range(len(sig) - 1, 0, -1) if sig[j] != sig[j - 1]), "一年內沒有變")
    rets = [c[j] / c[j - 1] - 1 for j in range(i - 29, i + 1)]
    r = rsi(c, i)
    return {
        "幣種": f"{SUPPORTED[sym]}({sym})",
        "日期": d[i],
        "收盤價": px(c[i]),
        f"{n}日均線": px(m),
        "距離均線%": round((c[i] / m - 1) * 100, 1),
        "規則訊號": "持有" if sig[-1] else "空手",
        "訊號理由": f"收盤價在{n}日均線{'上方' if sig[-1] else '下方'}",
        "要翻成另一個訊號": f"收盤價要{'跌破' if sig[-1] else '站上'}約 {px(m)}",
        "上次訊號改變日": changed,
        "RSI14": round(r, 1),
        "RSI分區": "偏超賣(<30)" if r < 30 else "偏超買(>70)" if r > 70 else "中間(30~70)",
        "7日漲跌%": round((c[i] / c[i - 7] - 1) * 100, 1),
        "30日平均每日波動%": round((sum(x * x for x in rets) / 30) ** 0.5 * 100, 2),
    }
