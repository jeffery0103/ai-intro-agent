"""策略實驗室:往「能上線、扣成本後能賺」的方向找策略。
- 開發期 2019~2023:只能在這裡挑策略與參數
- 期末考 2024~今天:挑完後只考一次,不准回頭改
- 每天收盤決定持有比例 0~1,隔天生效;換手成本 = 手續費 0.1% + 滑價 0.05%(乘上換手比例)
用法:python lab/strategy_lab.py   結果寫到 lab/strategy_result.md"""
import io, os, sys
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import predict_lab as pl

COST = 0.0015
DEV = ("2019-01-01", "2023-12-31")
EXAM = ("2024-01-01", "2099-12-31")
CRASH = -0.10              # 未來 7 天內曾跌超過 10% 算「大跌」


def ma(c, i, n):
    return c[i - n + 1:i + 1].mean()


def vol(c, i, n=30):
    r = c[i - n + 1:i + 1] / c[i - n:i] - 1
    return r.std() * np.sqrt(365)


def crash_probs(d, c, X):
    """大跌風險模型(梯度提升樹),滾動式:每 30 天重訓,只用答案已揭曉的資料。回傳 {i: 機率} 與考核數據。"""
    n = len(c); h = 7
    idx = [i for i in range(n - h) if X[i] is not None]
    y = {i: int(c[i + 1:i + h + 1].min() / c[i] - 1 <= CRASH) for i in idx}
    live = [i for i in range(n) if X[i] is not None]          # 最後 7 天沒有答案,但上線時還是要預測
    t0 = next(i for i in live if d[i] >= "2021-01-01")
    p = {}
    for blk in range(t0, n, 30):
        tr = [i for i in idx if i + h <= blk]
        te = [i for i in live if blk <= i < blk + 30]
        if not te:
            continue
        m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, l2_regularization=1.0,
                                           random_state=0).fit(np.array([X[i] for i in tr]), np.array([y[i] for i in tr]))
        for i, q in zip(te, m.predict_proba(np.array([X[i] for i in te]))[:, 1]):
            p[i] = q
    ev = [i for i in p if i in y]
    yy = np.array([y[i] for i in ev]); pp = np.array([p[i] for i in ev])
    q80 = np.quantile(pp, 0.8)
    stats = {"base": yy.mean(), "auc": roc_auc_score(yy, pp), "top20": yy[pp >= q80].mean(), "rest": yy[pp < q80].mean()}
    return p, stats


def strategies(c, crash, tv):
    """回傳 {策略名: 函式(i) -> 持有比例}。所有判斷只用 i 當天(含)以前的資料。"""
    trend4 = lambda i: np.mean([c[i] > ma(c, i, n) for n in (20, 50, 100, 200)])
    vt = lambda i: min(1.0, tv / vol(c, i))
    cr = lambda i: (1 - min(1.0, 2 * crash[i])) if i in crash else None
    return {
        "買進持有": lambda i: 1.0,
        "50日均線": lambda i: float(c[i] > ma(c, i, 50)),
        "多均線投票": trend4,
        "50日均線×波動目標": lambda i: float(c[i] > ma(c, i, 50)) * vt(i),
        "多均線投票×波動目標": lambda i: trend4(i) * vt(i),
        "多均線投票×波動目標×大跌風險": lambda i: trend4(i) * vt(i) * cr(i) if cr(i) is not None else None,
    }


def run(d, c, fn, a, b):
    """在 [a, b] 期間逐日回測,回傳每日報酬。"""
    rets = []; pos = 0.0
    for i in range(len(c) - 1):
        if not (a <= d[i] <= b):
            continue
        w = fn(i)
        if w is None:
            return None
        rets.append(-abs(w - pos) * COST + w * (c[i + 1] / c[i] - 1))
        pos = w
    return np.array(rets)


def stats(r, limit=0.10):
    eq = np.cumprod(1 + r); peak = np.maximum.accumulate(eq)
    years = len(r) / 365
    cagr = eq[-1] ** (1 / years) - 1
    sharpe = r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else 0
    # 歷史上任選一天開始,一年內虧到本金 limit 的機率
    hits = tot = 0
    for s in range(0, len(r) - 365, 5):
        e = np.cumprod(1 + r[s:s + 365]); tot += 1
        hits += e.min() <= 1 - limit
    return {"年化": cagr, "最大回撤": (eq / peak - 1).min(), "夏普": sharpe, "總報酬": eq[-1] - 1,
            "一年內虧到10%機率": hits / tot if tot else float("nan")}


def fmt(s):
    return f"{s['年化']:+.0%} | {s['最大回撤']:.0%} | {s['夏普']:.2f} | {s['一年內虧到10%機率']:.0%}"


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    f = io.open(os.path.join(here, "strategy_result.md"), "w", encoding="utf-8")
    f.write("# 策略實驗結果\n\n換手成本 0.15%(手續費 0.1% + 滑價 0.05%)。開發期挑策略,期末考只考一次。\n")
    data = {}
    for sym in ["BTC", "ETH"]:
        d, c, X = pl.features(sym)
        crash, cs = crash_probs(d, c, X)
        data[sym] = (d, c, crash)
        f.write(f"\n## {sym} 大跌風險模型(未來 7 天內跌超過 10%)\n\n平時發生率 {cs['base']:.1%};AUC {cs['auc']:.3f};"
                f"模型認為風險最高的 20% 日子,實際發生率 **{cs['top20']:.1%}**,其他日子 {cs['rest']:.1%}。\n")

    # 1) 開發期:挑波動目標參數(只看開發期的夏普),大跌風險模型因為 2021 才開始,開發期改用 2021~2023
    f.write("\n## 開發期 2019~2023(大跌風險策略只有 2021~2023)\n\n| 幣 | 策略 | 波動目標 | 年化 | 最大回撤 | 夏普 | 一年內虧到10%機率 |\n|---|---|---|---|---|---|---|\n")
    dev_score = {}
    for sym, (d, c, crash) in data.items():
        for tv in (0.3, 0.5, 0.8):
            for name, fn in strategies(c, crash, tv).items():
                if "波動目標" not in name and tv != 0.5:
                    continue
                a = "2021-01-01" if "大跌風險" in name else DEV[0]
                r = run(d, c, fn, a, DEV[1])
                if r is None:
                    continue
                s = stats(r); key = (name, tv if "波動目標" in name else None)
                dev_score.setdefault(key, []).append(s["夏普"])
                f.write(f"| {sym} | {name} | {key[1] or '-'} | {fmt(s)} |\n")
    # 兩個幣平均夏普最高者 = 開發期選出的策略
    avg = {k: np.mean(v) for k, v in dev_score.items() if len(v) == 2}
    pick = max(avg, key=avg.get)
    f.write(f"\n開發期兩幣平均夏普最高:**{pick[0]}**(波動目標 {pick[1]})。\n")

    # 2) 期末考:所有策略都列出來,但「選出的」只有一個
    f.write("\n## 期末考 2024~今天(只考一次)\n\n| 幣 | 策略 | 波動目標 | 年化 | 最大回撤 | 夏普 | 一年內虧到10%機率 |\n|---|---|---|---|---|---|---|\n")
    port = {}
    for sym, (d, c, crash) in data.items():
        for key in sorted(avg, key=lambda k: -avg[k]):
            name, tv = key
            r = run(d, c, strategies(c, crash, tv or 0.5)[name], *EXAM)
            port.setdefault(key, []).append(r)
            mark = " ← 開發期選出" if key == pick else ""
            f.write(f"| {sym} | {name}{mark} | {tv or '-'} | {fmt(stats(r))} |\n")
    f.write("\n### 期末考:BTC + ETH 各半的組合\n\n| 策略 | 波動目標 | 年化 | 最大回撤 | 夏普 | 一年內虧到10%機率 |\n|---|---|---|---|---|---|\n")
    for key in sorted(avg, key=lambda k: -avg[k]):
        a, b = port[key]; m = min(len(a), len(b))
        r = (a[:m] + b[:m]) / 2
        f.write(f"| {key[0]}{' ← 開發期選出' if key == pick else ''} | {key[1] or '-'} | {fmt(stats(r))} |\n")
    f.close()
    print(open(os.path.join(here, "strategy_result.md"), encoding="utf-8").read())
