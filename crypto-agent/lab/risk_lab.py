"""老師回饋的驗證:(1) 槓桿評估:同一策略開 1/2/3/5 倍,回撤與爆倉;(2) 價格以外的指標:穩定幣總量、鏈上交易數、TVL
跟未來 30 天報酬有沒有關係(開發期 / 期末考分開)。
槓桿模型(簡化):逐倉,每日收盤結算;當日最低價跌到 維持保證金 0.5% 的強平價就算爆倉,該部位歸零。
成本 0.15%(以名目部位計),另計永續資金費(用該幣 2019 年起的歷史,沒有資料的日子當 0)。
用法:python lab/risk_lab.py   結果寫到 lab/risk_result.md"""
import io, json, os, sys, urllib.request
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import market, strategy
import predict_lab as pl

COST = 0.0015
MMR = 0.005
HERE = os.path.dirname(os.path.abspath(__file__))
A, SPLIT = "2019-01-01", "2024-01-01"


def ohlc(sym):
    """抓含最低價的日線(只給這個實驗用)。"""
    p = os.path.join(market.DATA, f"{sym}USDT_low.json")
    rows = json.load(open(p)) if os.path.exists(p) else []
    start = rows[-1][0] + 86400000 if rows else 1514764800000
    while True:
        k = market._spot(f"/api/v3/klines?symbol={sym}USDT&interval=1d&startTime={start}&limit=1000")
        if not k:
            break
        rows += [[x[0], float(x[3]), float(x[4])] for x in k if x[6] < market.time.time() * 1000]
        if len(k) < 1000:
            break
        start = k[-1][0] + 86400000
    json.dump(rows, open(p, "w"))
    return rows


def sim(sym, lev, a, b):
    rows = ohlc(sym); d = [market.day(r[0]) for r in rows]; low = [r[1] for r in rows]; c = [r[2] for r in rows]
    fd = pl.funding_daily(sym)
    eq = peak = 1.0; mdd = 0.0; pos = 0.0; liq = 0; n = 0; floor = 1.0
    for i in range(201, len(c) - 1):
        if not (a <= d[i] < b):
            continue
        n += 1
        w = strategy.weight(c, i) * lev
        eq *= 1 - abs(w - pos) * COST
        pos = w
        if w > 0:
            # 假設這筆資金全押保證金:逐倉、不留現金,跌幅到 (1/lev - MMR) 就爆倉
            drop = low[i + 1] / c[i] - 1
            if lev > 1 and drop <= -(1 / lev - MMR):
                eq *= 1 - min(1.0, w / lev)             # 投入的保證金歸零
                liq += 1; pos = 0.0
            else:
                eq *= 1 + w * (c[i + 1] / c[i] - 1) - (w * fd.get(d[i], 0) * 3 if lev > 1 else 0)
        peak = max(peak, eq); mdd = min(mdd, eq / peak - 1); floor = min(floor, eq)
    return {"報酬%": round((eq - 1) * 100), "最大回撤%": round(mdd * 100), "爆倉": liq, "最低點(本金=1)": round(floor, 2), "天": n}


def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (crypto-agent learning project)"}), timeout=40))


def indicators():
    st = {market.day(int(x["date"]) * 1000): x["totalCirculatingUSD"].get("peggedUSD", 0) for x in get("https://stablecoins.llama.fi/stablecoincharts/all")}
    tvl = {market.day(int(x["date"]) * 1000): x["tvl"] for x in get("https://api.llama.fi/v2/historicalChainTvl")}
    tx = {market.day(int(x["x"]) * 1000): x["y"] for x in get("https://api.blockchain.info/charts/n-transactions?timespan=all&format=json&sampled=false")["values"]}
    return {"穩定幣總量 30 天變化": st, "DeFi 鎖倉量 TVL 30 天變化": tvl, "比特幣鏈上交易數 30 天變化": tx}


def corr_table(f):
    rows = market.load("BTC"); d = [r[0] for r in rows]; c = np.array([r[1] for r in rows])
    f.write("\n## 價格以外的指標:30 天變化 vs BTC 未來 30 天報酬\n\n每 30 天取一個不重疊的點,雜訊範圍約 ±2/√N。\n\n| 指標 | 開發期 2019~2023 相關(N) | 期末考 2024~ 相關(N) |\n|---|---|---|\n")
    for name, s in indicators().items():
        cells = []
        for a, b in ((A, SPLIT), (SPLIT, "2099")):
            x, y = [], []
            for i in range(30, len(c) - 30, 30):
                if not (a <= d[i] < b):
                    continue
                v0, v1 = s.get(d[i - 30]), s.get(d[i])
                if v0 and v1:
                    x.append(v1 / v0 - 1); y.append(c[i + 30] / c[i] - 1)
            r = np.corrcoef(x, y)[0, 1] if len(x) > 3 else float("nan")
            cells.append(f"{r:+.2f}({len(x)},雜訊 ±{2 / np.sqrt(max(len(x), 1)):.2f})")
        f.write(f"| {name} | {cells[0]} | {cells[1]} |\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    f = io.open(os.path.join(HERE, "risk_result.md"), "w", encoding="utf-8")
    f.write("# 風險與指標實驗\n\n## 槓桿評估:同一策略放大幾倍(開發期 2019~2023 / 期末考 2024~)\n\n簡化模型:逐倉、看每日最低價、維持保證金 0.5%。\n\n")
    f.write("| 幣 | 槓桿 | 開發期報酬% | 回撤% | 爆倉 | 期末考報酬% | 回撤% | 爆倉 |\n|---|---|---|---|---|---|---|---|\n")
    for sym in ("BTC", "ETH"):
        for lev in (1, 2, 3, 5, 10):
            x = sim(sym, lev, A, SPLIT); y = sim(sym, lev, SPLIT, "2099")
            f.write(f"| {sym} | {lev}x | {x['報酬%']} | {x['最大回撤%']} | {x['爆倉']} | {y['報酬%']} | {y['最大回撤%']} | {y['爆倉']} |\n")
    corr_table(f)
    f.close()
    print(open(os.path.join(HERE, "risk_result.md"), encoding="utf-8").read())
