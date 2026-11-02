"""預測實驗室:哪個模型能在「沒看過的資料」上贏過笨方法?
- 目標:隔天漲跌(h=1)、7 天後漲跌(h=7)
- 材料(都只用當天收盤前就知道的資料):多期報酬、離均線多遠、RSI、波動、成交量變化、資金費率
- 考試:滾動式樣本外驗證。2021 起每 30 天重新訓練一次,只用「標準答案已經揭曉」的過去資料訓練,預測接下來 30 天
- 對照組:永遠猜漲、50 日均線規則、7 日動能
用法:python lab/predict_lab.py   結果寫到 lab/predict_result.md"""
import io, json, os, sys, time, urllib.request
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import market

FEE = 0.001
TEST_START = "2021-01-01"
RETRAIN = 30


def funding_daily(sym):
    """資金費率歷史(快取在 data/),換成每天平均。"""
    path = os.path.join(market.DATA, f"{sym}USDT_funding.json")
    rows = json.load(open(path)) if os.path.exists(path) else []
    start = rows[-1][0] + 1 if rows else 1546300800000
    while True:
        k = market._get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}USDT&startTime={start}&limit=1000")
        if not k:
            break
        rows += [[x["fundingTime"], float(x["fundingRate"])] for x in k]
        start = k[-1]["fundingTime"] + 1
        if len(k) < 1000:
            break
        time.sleep(0.2)
    json.dump(rows, open(path, "w"))
    day = {}
    for t, f in rows:
        day.setdefault(market.day(t), []).append(f)
    return {d: sum(v) / len(v) for d, v in day.items()}


def features(sym):
    market.load(sym)
    raw = json.load(open(os.path.join(market.DATA, f"{sym}USDT_1d.json")))
    d = [market.day(r[0]) for r in raw]; c = np.array([r[1] for r in raw]); v = np.array([r[2] for r in raw])
    fd = funding_daily(sym)
    f = np.array([fd.get(x, np.nan) for x in d])
    n = len(c); X = []; ok = []
    for i in range(n):
        if i < 200 or np.isnan(f[i - 20:i + 1]).any():
            X.append(None); continue
        ret = lambda k: c[i] / c[i - k] - 1
        dr = c[i - 29:i + 1] / c[i - 30:i] - 1
        X.append([ret(1), ret(3), ret(7), ret(14), ret(30),
                  c[i] / c[i - 19:i + 1].mean() - 1, c[i] / c[i - 49:i + 1].mean() - 1, c[i] / c[i - 199:i + 1].mean() - 1,
                  market.rsi(list(c), i) / 100, dr.std(), v[i] / v[i - 29:i + 1].mean(),
                  f[i - 2:i + 1].mean() * 1000, f[i - 20:i + 1].mean() * 1000])
    return d, c, X


NAMES = ["1日報酬", "3日報酬", "7日報酬", "14日報酬", "30日報酬", "離20日線", "離50日線", "離200日線",
         "RSI", "30日波動", "成交量比", "資金費率3日", "資金費率21日"]


def walk_forward(d, c, X, h):
    """回傳 test 區每天的 {日期, 實際, 各模型機率}。"""
    n = len(c)
    idx = [i for i in range(n - h) if X[i] is not None]
    y = {i: int(c[i + h] > c[i]) for i in idx}
    t0 = next(i for i in idx if d[i] >= TEST_START)
    out = []
    for blk in range(t0, n - h, RETRAIN):
        train = [i for i in idx if i + h <= blk]            # 標準答案在 blk 之前就揭曉的才拿來訓練
        test = [i for i in idx if blk <= i < min(blk + RETRAIN, n - h)]
        if not test:
            continue
        Xtr = np.array([X[i] for i in train]); ytr = np.array([y[i] for i in train]); Xte = np.array([X[i] for i in test])
        lr = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000)).fit(Xtr, ytr)
        gb = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, l2_regularization=1.0,
                                            random_state=0).fit(Xtr, ytr)
        base = ytr.mean()
        p_lr = lr.predict_proba(Xte)[:, 1]; p_gb = gb.predict_proba(Xte)[:, 1]
        for k, i in enumerate(test):
            out.append({"i": i, "date": d[i], "y": y[i],
                        "永遠猜漲": 1.0, "訓練期上漲比例": base,
                        "50日均線規則": 1.0 if X[i][6] > 0 else 0.0, "7日動能": 1.0 if X[i][2] > 0 else 0.0,
                        "邏輯迴歸": p_lr[k], "梯度提升樹": p_gb[k]})
    return out


def trade(rows, c, model, thr=0.5):
    """每天收盤時:機率 > thr 就持有到隔天,否則空手;換手扣 0.1%。"""
    eq = peak = 1.0; mdd = 0.0; pos = 0; days_in = 0
    for r in rows:
        i = r["i"]; want = 1 if r[model] > thr else 0
        if want != pos:
            eq *= 1 - FEE; pos = want
        if pos:
            eq *= c[i + 1] / c[i]; days_in += 1
        peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
    return eq - 1, mdd, days_in / len(rows)


MODELS = ["永遠猜漲", "50日均線規則", "7日動能", "邏輯迴歸", "梯度提升樹"]


def report(sym, h, rows, c, f):
    y = np.array([r["y"] for r in rows]); N = len(y); base = y.mean()
    neff = N / h                                          # 7 天目標的答案彼此重疊,有效樣本約少 7 倍
    se = (base * (1 - base) / neff) ** 0.5
    f.write(f"\n### {sym} 預測 {h} 天後漲跌({rows[0]['date']}~{rows[-1]['date']},{N} 天,實際上漲比例 {base:.1%})\n\n")
    f.write("| 模型 | 命中率 | 比永遠猜漲多 | AUC | 照它交易的報酬 | 最大回撤 | 持有時間 |\n|---|---|---|---|---|---|---|\n")
    res = {}
    for m in MODELS:
        p = np.array([r[m] for r in rows]); pred = (p > 0.5).astype(int)
        acc = (pred == y).mean()
        auc = roc_auc_score(y, p) if len(set(p)) > 1 else 0.5
        ret, mdd, tin = trade(rows, c, m)
        res[m] = (acc, auc, ret)
        f.write(f"| {m} | {acc:.1%} | {(acc - base) * 100:+.1f} 點 | {auc:.3f} | {ret:+.0%} | {mdd:.0%} | {tin:.0%} |\n")
    f.write(f"\n雜訊範圍:命中率要比永遠猜漲多約 **{2 * se * 100:.1f} 點**以上,才不太像運氣(兩個標準誤)。AUC 0.5 = 完全沒有排序能力。\n")
    for m in ("邏輯迴歸", "梯度提升樹"):
        p = np.array([r[m] for r in rows])
        f.write(f"\n{m}「信心」對不對得上實際(機率分五組):\n\n| 模型說的上漲機率 | 天數 | 實際上漲比例 |\n|---|---|---|\n")
        qs = np.quantile(p, [0, .2, .4, .6, .8, 1])
        for a, b in zip(qs[:-1], qs[1:]):
            mask = (p >= a) & (p <= b)
            f.write(f"| {a:.2f}~{b:.2f} | {mask.sum()} | {y[mask].mean():.1%} |\n")
    f.write("\n每年命中率(看穩不穩定):\n\n| 年 | 實際上漲比例 | " + " | ".join(MODELS[1:]) + " |\n|---|---|" + "---|" * 4 + "\n")
    for yr in sorted({r["date"][:4] for r in rows}):
        rr = [r for r in rows if r["date"].startswith(yr)]; yy = np.array([r["y"] for r in rr])
        f.write(f"| {yr} | {yy.mean():.0%} | " + " | ".join(f"{((np.array([r[m] for r in rr]) > 0.5) == yy).mean():.0%}" for m in MODELS[1:]) + " |\n")
    return res


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    f = io.open(os.path.join(here, "predict_result.md"), "w", encoding="utf-8")
    f.write("# 預測實驗結果(滾動式樣本外驗證)\n\n每 30 天重新訓練,只用標準答案已揭曉的過去資料;交易一律扣 0.1% 手續費。\n")
    summary = []
    for sym in ["BTC", "ETH"]:
        d, c, X = features(sym)
        for h in (1, 7):
            rows = walk_forward(d, c, X, h)
            res = report(sym, h, rows, c, f)
            summary.append((sym, h, res))
    f.close()
    for sym, h, res in summary:
        print(sym, h, {m: f"{a:.3f}/{u:.3f}/{r:+.2f}" for m, (a, u, r) in res.items()})
