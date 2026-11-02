"""延伸實驗:情緒(恐懼與貪婪指數)、資安事件(DeFi/交易所被駭)、其他幣。
上線標準(比上一輪更嚴):因為 2024 起的期末考已經看過一次,新東西要在「開發期」和「期末考」都贏過
目前上線的策略(50 日均線 × 波動目標 30%)才會換上去。
用法:python lab/extra_lab.py   結果寫到 lab/extra_result.md"""
import io, json, os, sys, urllib.request
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import market
from strategy_lab import ma, vol, run, stats, fmt, DEV, EXAM

HERE = os.path.dirname(os.path.abspath(__file__))


def get(url, cache):
    p = os.path.join(market.DATA, cache)
    if not os.path.exists(p):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        open(p, "wb").write(urllib.request.urlopen(req, timeout=60).read())
    return json.load(open(p, encoding="utf-8"))


def series(sym):
    rows = market.load(sym)
    return [r[0] for r in rows], np.array([r[1] for r in rows])


def base_w(c, i):
    """目前上線的策略。"""
    return float(c[i] > ma(c, i, 50)) * min(1.0, 0.30 / vol(c, i))


def fwd(c, i, h):
    return c[i + h] / c[i] - 1 if i + h < len(c) else None


# ---------- A. 恐懼與貪婪指數 ----------
def fear_greed():
    data = get("https://api.alternative.me/fng/?limit=0&format=json", "fng.json")["data"]
    return {market.day(int(x["timestamp"]) * 1000): int(x["value"]) for x in data}


def exp_fng(f, coins):
    fg = fear_greed()
    f.write("\n## A. 恐懼與貪婪指數(0 = 極度恐懼,100 = 極度貪婪)\n\n"
            f"資料 {min(fg)} ~ {max(fg)}。先看「指數高低」跟「之後 7 / 30 天報酬」有沒有關係(開發期 / 期末考分開看):\n\n")
    for sym, (d, c) in coins.items():
        f.write(f"**{sym}**\n\n| 指數區間 | 開發期天數 | 開發期 7天後平均 | 開發期 30天後平均 | 期末考天數 | 期末考 7天後平均 | 期末考 30天後平均 |\n|---|---|---|---|---|---|---|\n")
        for lo, hi in ((0, 20), (20, 40), (40, 60), (60, 80), (80, 101)):
            cells = []
            for a, b in (DEV, EXAM):
                ii = [i for i in range(len(c)) if a <= d[i] <= b and d[i] in fg and lo <= fg[d[i]] < hi]
                r7 = [fwd(c, i, 7) for i in ii if fwd(c, i, 7) is not None]
                r30 = [fwd(c, i, 30) for i in ii if fwd(c, i, 30) is not None]
                cells += [str(len(ii)), f"{np.mean(r7):+.1%}" if r7 else "-", f"{np.mean(r30):+.1%}" if r30 else "-"]
            f.write(f"| {lo}~{min(hi, 100)} | " + " | ".join(cells) + " |\n")
        f.write("\n")
    # 疊加在上線策略上的幾種用法(規則少,避免過度擬合)
    def mk(c, d, kind):
        def w(i):
            b = base_w(c, i); x = fg.get(d[i])
            if x is None:
                return b
            if kind == "貪婪≥80 減半":
                return b * (0.5 if x >= 80 else 1)
            if kind == "恐懼≤20 時均線下方也持有一半":
                return max(b, 0.5 * min(1.0, 0.30 / vol(c, i))) if x <= 20 else b
            if kind == "恐懼≤25 時暫停(跟著情緒避險)":
                return 0.0 if x <= 25 else b
            return b
        return w
    kinds = ["上線策略", "貪婪≥80 減半", "恐懼≤20 時均線下方也持有一半", "恐懼≤25 時暫停(跟著情緒避險)"]
    return compare(f, coins, lambda c, d, k: mk(c, d, k), kinds, "A 的策略版本")


def compare(f, coins, maker, kinds, title, start=None):
    """各版本在開發期、期末考的成績(各幣等權組合)。"""
    f.write(f"\n### {title}(各幣等權組合)\n\n| 版本 | 開發期 年化 | 回撤 | 夏普 | 虧10%機率 | 期末考 年化 | 回撤 | 夏普 | 虧10%機率 |\n|---|---|---|---|---|---|---|---|---|\n")
    out = {}
    for k in kinds:
        row = []
        for a, b in (DEV, EXAM):
            a = max(a, start) if start else a
            rs = [run(d, c, maker(c, d, k), max(a, d[201]), b) for d, c in coins.values()]
            m = min(len(r) for r in rs)
            r = np.mean([x[-m:] for x in rs], axis=0)
            s = stats(r); row.append(s)
        out[k] = row
        f.write(f"| {k} | {fmt(row[0])} | {fmt(row[1])} |\n")
    base = out[kinds[0]]
    win = [k for k in kinds[1:] if out[k][0]["夏普"] > base[0]["夏普"] and out[k][1]["夏普"] > base[1]["夏普"]]
    f.write(f"\n開發期與期末考夏普都贏過上線策略的:**{'、'.join(win) if win else '沒有'}**\n")
    return out, win


# ---------- B. 資安事件(被駭) ----------
def exp_hacks(f, coins):
    hacks = get("https://api.llama.fi/hacks", "hacks.json")
    f.write("\n## B. 加密貨幣被駭事件(DeFiLlama 資料庫)\n\n"
            "事件研究:重大被駭事件當天收盤買進,之後 1 / 7 / 30 天的平均報酬,和「隨便哪一天」的平均報酬比。"
            "差距要大於雜訊範圍(約 2 個標準誤)才算有影響。\n")
    for th in (50e6, 100e6):
        ev = sorted({market.day(h["date"] * 1000) for h in hacks if (h.get("amount") or 0) >= th})
        f.write(f"\n**被盜金額 ≥ {th / 1e6:.0f}M 美元:{len(ev)} 天有事件**({ev[0]} ~ {ev[-1]})\n\n"
                "| 幣 | 期間 | 事件後平均 | 任何一天平均 | 差距 | 雜訊範圍(2 標準誤) | 事件後下跌比例 |\n|---|---|---|---|---|---|---|\n")
        for sym, (d, c) in coins.items():
            pos = {x: i for i, x in enumerate(d)}
            for h in (1, 7, 30):
                allr = np.array([fwd(c, i, h) for i in range(200, len(c) - h)])
                er = np.array([fwd(c, pos[x], h) for x in ev if x in pos and fwd(c, pos[x], h) is not None])
                if len(er) < 5:
                    continue
                se = allr.std() / np.sqrt(len(er))       # 事件之間大多不重疊,當作獨立樣本
                f.write(f"| {sym} | {h} 天 | {er.mean():+.2%} | {allr.mean():+.2%} | {er.mean() - allr.mean():+.2%} | ±{2 * se:.2%} | {(er < 0).mean():.0%} |\n")
    # 最大的 10 件
    top = sorted(hacks, key=lambda h: -(h.get("amount") or 0))[:10]
    f.write("\n最大的 10 件,BTC 之後 7 天的漲跌:\n\n| 日期 | 事件 | 金額(M 美元) | BTC 7 天 | ETH 7 天 |\n|---|---|---|---|---|\n")
    for h in top:
        x = market.day(h["date"] * 1000); cells = []
        for sym in ("BTC", "ETH"):
            d, c = coins[sym]; pos = {y: i for i, y in enumerate(d)}
            r = fwd(c, pos[x], 7) if x in pos else None
            cells.append(f"{r:+.1%}" if r is not None else "-")
        f.write(f"| {x} | {h['name']} | {h['amount'] / 1e6:.0f} | {cells[0]} | {cells[1]} |\n")


# ---------- C. 其他幣 ----------
def exp_coins(f):
    f.write("\n## C. 其他幣\n")
    (db, cb), (de, ce) = series("BTC"), series("ETH")
    rb = dict(zip(db[1:], cb[1:] / cb[:-1] - 1)); re_ = dict(zip(de[1:], ce[1:] / ce[:-1] - 1))
    days = sorted(set(rb) & set(re_))
    x = np.array([rb[t] for t in days[:-1]]); y = np.array([re_[t] for t in days[1:]])
    same = np.corrcoef([rb[t] for t in days], [re_[t] for t in days])[0, 1]
    f.write(f"\n**BTC 今天漲跌能不能預測 ETH 明天?** 相關係數 {np.corrcoef(x, y)[0, 1]:+.3f}(同一天的相關是 {same:+.3f})。"
            f"樣本 {len(x)} 天,雜訊範圍約 ±{2 / np.sqrt(len(x)):.3f}。\n")
    five = {s: series(s) for s in ["BTC", "ETH", "SOL", "BNB", "XRP"]}
    first = max(d[0] for d, _ in five.values())
    f.write(f"\n**分散到 5 個幣**(SOL 資料從 {first} 才有,所以開發期只用 2021~2023):\n")
    wf = lambda c, d, k: (lambda i: base_w(c, i))
    two = {s: five[s] for s in ("BTC", "ETH")}
    out = {}
    for name, coins in (("BTC+ETH(目前)", two), ("5 幣等權", five)):
        out[name] = compare(f, coins, wf, ["上線策略"], name, start="2021-01-01")[0]["上線策略"]
    # BTC 趨勢當總開關:BTC 在 50 日均線下方時,其他幣也不持有
    pos_b = {x: i for i, x in enumerate(five["BTC"][0])}
    cbtc = five["BTC"][1]
    def gate(c, d, k):
        def w(i):
            j = pos_b.get(d[i])
            b = base_w(c, i)
            return b if k == "上線策略" or j is None or cbtc[j] > ma(cbtc, j, 50) else 0.0
        return w
    compare(f, five, gate, ["上線策略", "BTC 在均線下方時全部空手"], "5 幣:加上 BTC 總開關", start="2021-01-01")
    return out


if __name__ == "__main__":
    f = io.open(os.path.join(HERE, "extra_result.md"), "w", encoding="utf-8")
    f.write("# 延伸實驗:情緒、資安事件、其他幣\n\n成本 0.15%;開發期 2019~2023、期末考 2024~今天。"
            "**期末考上一輪已經看過一次**,所以新版本要開發期和期末考都贏過上線策略才算數。\n")
    coins = {s: series(s) for s in ("BTC", "ETH")}
    exp_fng(f, coins)
    exp_hacks(f, coins)
    exp_coins(f)
    f.close()
    print(open(os.path.join(HERE, "extra_result.md"), encoding="utf-8").read())
