"""回測:(1) 樣本外驗證——均線天數只用訓練期挑,再到沒看過的測試期考試;
(2) 對照使用者的虧損上限——歷史上任選一天開始,一年內虧到上限的機率。
用法:python backtest.py [BTC ETH ...]  結果寫到 data/backtest.json 與 backtest_result.md"""
import io, json, os, sys
import market

FEE = 0.001                          # 每次買或賣 0.1%
CANDIDATES = [10, 20, 30, 50, 100, 150, 200]
SPLIT = "2024-01-01"                  # 之前 = 訓練期,之後 = 測試期(樣本外)


def multipliers(c, n):
    """每天資產變成幾倍:用「昨天收盤」的訊號決定今天有沒有持有,換手當天扣手續費。n=None 是買進持有。"""
    g = [1.0] * len(c); pos = 0
    for i in range(201, len(c)):
        want = 1 if n is None else market.signal(c, i - 1, n)
        m = 1.0
        if want != pos:
            m *= 1 - FEE; pos = want
        if pos:
            m *= c[i] / c[i - 1]
        g[i] = m
    return g


def stats(g, a, b):
    eq = peak = 1.0; mdd = 0.0
    for i in range(a, b):
        eq *= g[i]; peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
    return {"報酬%": round((eq - 1) * 100, 1), "最大回撤%": round(mdd * 100, 1)}


def hit_rate(g, a, b, limit, horizon=365):
    """從 [a, b-horizon) 每一天開始,一年內資產曾跌到本金的 (1-limit) 以下的比例。"""
    hits = total = 0
    for s in range(a, b - horizon):
        eq = 1.0; total += 1
        for i in range(s, s + horizon):
            eq *= g[i]
            if eq <= 1 - limit:
                hits += 1; break
    return round(hits / total * 100) if total else None


def analyze(sym, max_loss=None):
    rows = market.load(sym)
    d = [r[0] for r in rows]; c = [r[1] for r in rows]
    a = 201; s = next(i for i, x in enumerate(d) if x >= market.START and i >= a)
    t = d.index(next(x for x in d if x >= SPLIT)); b = len(c)
    gs = {n: multipliers(c, n) for n in CANDIDATES}; bh = multipliers(c, None)
    train = {n: stats(gs[n], s, t) for n in CANDIDATES}
    best = max(CANDIDATES, key=lambda n: train[n]["報酬%"])
    test = {n: stats(gs[n], t, b) for n in CANDIDATES}
    out = {"幣種": sym, "訓練期": f"{d[s]}~{d[t-1]}", "測試期": f"{d[t]}~{d[-1]}",
           "訓練期各均線": train, "訓練期最佳均線": best, "訓練期買進持有": stats(bh, s, t),
           "測試期各均線": test, "測試期買進持有": stats(bh, t, b),
           "測試期最佳均線(事後才知道)": max(CANDIDATES, key=lambda n: test[n]["報酬%"])}
    if max_loss:
        out["一年內虧到上限的機率%"] = {f"{n}日均線": hit_rate(gs[n], s, b, max_loss) for n in (best, 50)}
        out["一年內虧到上限的機率%"]["買進持有"] = hit_rate(bh, s, b, max_loss)
    return out


def write_md(results, path):
    f = io.open(path, "w", encoding="utf-8")
    f.write("# 回測結果(含手續費 0.1%,日線收盤)\n\n")
    for r in results:
        f.write(f"## {r['幣種']}\n訓練期 {r['訓練期']} / 測試期 {r['測試期']}\n\n")
        f.write("| 均線天數 | 訓練期報酬% | 訓練期最大回撤% | 測試期報酬% | 測試期最大回撤% |\n|---|---|---|---|---|\n")
        for n in CANDIDATES:
            tr, te = r["訓練期各均線"][n], r["測試期各均線"][n]
            mark = " ← 訓練期挑出" if n == r["訓練期最佳均線"] else ""
            f.write(f"| {n}{mark} | {tr['報酬%']} | {tr['最大回撤%']} | {te['報酬%']} | {te['最大回撤%']} |\n")
        bt, be = r["訓練期買進持有"], r["測試期買進持有"]
        f.write(f"| 買進持有 | {bt['報酬%']} | {bt['最大回撤%']} | {be['報酬%']} | {be['最大回撤%']} |\n\n")
        f.write(f"測試期事後最好的是 {r['測試期最佳均線(事後才知道)']} 日均線。\n\n")
        if "一年內虧到上限的機率%" in r:
            f.write("歷史上任選一天開始,一年內帳戶曾經虧到上限的機率:" +
                    "、".join(f"{k} {v}%" for k, v in r["一年內虧到上限的機率%"].items()) + "\n\n")
    f.close()


if __name__ == "__main__":
    syms = sys.argv[1:] or ["BTC", "ETH"]
    import storage
    prof = storage.load("profile.json")
    limit = prof["max_loss_pct"] / 100 if prof else 0.10
    res = [analyze(s, limit) for s in syms]
    json.dump(res, open(os.path.join(market.DATA, "backtest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(res, os.path.join(market.HERE, "backtest_result.md"))
    print(open(os.path.join(market.HERE, "backtest_result.md"), encoding="utf-8").read())
