"""Binance 公開 API 抓日線(不需要金鑰),存到 data/ 當快取;指標全部用程式算,不用 LLM。"""
import json, os, time, urllib.error, urllib.request, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SUPPORTED = {"BTC": "比特幣", "ETH": "以太幣", "SOL": "Solana", "BNB": "幣安幣", "XRP": "瑞波幣"}
START = "2018-01-01"


SPOT_HOSTS = ["https://api.binance.com", "https://data-api.binance.vision"]   # 主站被地區封鎖時改用公開資料站


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (crypto-agent learning project)"})   # OKX 會擋沒有 User-Agent 的請求
    return json.load(urllib.request.urlopen(req, timeout=20))


_binance_blocked_until = 0.0     # Binance 回 429/418 後,這個時間前都不碰它(越抓越久會被封 IP)


def _spot(path):
    global _binance_blocked_until
    if time.time() < _binance_blocked_until:
        raise RuntimeError("Binance 限流中,先不送請求")
    err = None
    for h in SPOT_HOSTS:
        try:
            return _get(h + path)
        except urllib.error.HTTPError as e:
            if e.code in (418, 429):                # 418 = 已經被封 IP,429 = 快要被封
                wait = int(e.headers.get("Retry-After") or 3600)
                _binance_blocked_until = time.time() + wait
                print(f"Binance 回 {e.code},{wait} 秒內改用備援", flush=True)
                raise
            err = e
        except Exception as e:
            err = e
    raise err


def day(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


LAST_SOURCE = {}       # 每個幣這次實際用了哪個資料來源,給 Tracing 看


def _binance(sym, start, now):
    rows = []
    while start < now:
        k = _spot(f"/api/v3/klines?symbol={sym}USDT&interval=1d&startTime={start}&limit=1000")
        k = [x for x in k if x[6] < now]           # x[6] = 收盤時間,還沒收盤的今天不要
        if not k:
            break
        rows += [[x[0], float(x[4]), float(x[5])] for x in k]
        start = k[-1][0] + 86400000
    return rows


def _okx(sym, start, now):
    """備援:OKX 的 UTC 日線(跟 Binance 一樣以 UTC 0 點切日,收盤價差異約 0.01~0.05%)。從新往舊翻頁。"""
    rows, after = [], now
    while True:
        k = _get(f"https://www.okx.com/api/v5/market/history-candles?instId={sym}-USDT&bar=1Dutc&limit=100&after={after}")["data"]
        if not k:
            break
        rows += [[int(x[0]), float(x[4]), float(x[5])] for x in k if x[8] == "1" and int(x[0]) >= start]
        after = int(k[-1][0])
        if after <= start:
            break
        time.sleep(0.12)                            # OKX 公開 API 每 2 秒 20 次
    return sorted(rows)


def load(sym):
    """回傳 [(日期, 收盤價), ...],只含已收盤的日線(UTC 0 點 = 台灣 8 點收盤)。
    先用 Binance(主站 → 公開資料站),都失敗才用 OKX:資料來源不能只靠一家交易所。"""
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, f"{sym}USDT_1d.json")
    rows = json.load(open(path)) if os.path.exists(path) else []
    start = rows[-1][0] + 86400000 if rows else int(dt.datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    now = int(time.time() * 1000)
    if rows and rows[-1][0] >= (now // 86400000 - 1) * 86400000:    # 昨天(最新已收盤)那根已經有了,不用再問交易所
        LAST_SOURCE.setdefault(sym, "快取")
        return [(day(r[0]), r[1]) for r in rows]
    try:
        new = _binance(sym, start, now); LAST_SOURCE[sym] = "Binance"
    except Exception:
        new = _okx(sym, start, now); LAST_SOURCE[sym] = "OKX(Binance 連不上)"
    rows += new
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
