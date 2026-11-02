"""模擬帳戶(跨天的記憶):資金平分給每個幣,每天收盤照目標持有比例調整,含手續費。
同時記三條路線(strategy.TRACKS):上線的「策略」、對照組「純50日均線」「買進持有」,每天一起對帳。
「策略」總值低於本金 ×(1−上限)就全部賣出並暫停,等使用者檢討後用 --resume 繼續(Human-in-the-Loop)。
用法:python sim.py            更新到最新收盤
      python sim.py --resume   解除暫停
      python sim.py --reset    清掉帳戶重新開始"""
import json, sys
import market, storage, strategy

FEE = 0.001
BAND = 0.05            # 目標比例跟目前差不到 5 個百分點就不調,省手續費
NAME = "ledger.json"
VERSION = 2            # 1 = 全買全賣的舊版;舊版帳戶會被重新開始


def load():
    L = storage.load(NAME)
    return L if L and L.get("version") == VERSION else None


def _save(L):
    storage.save(NAME, L)


def reset():
    storage.delete(NAME)


def resume():
    """解除暫停;之後的虧損上限從目前總值重新算。"""
    L = load()
    if not L or not L["halted"]:
        return None
    L["ref"] = L["history"][-1]["策略"]; L["halted"] = None; _save(L)
    return L["ref"]


def _value(book, px):
    return sum(s["cash"] + s["qty"] * px[k] for k, s in book.items())


def _rebalance(sl, w, p, force=False):
    """把一個幣的部位調到目標比例 w;回傳交易紀錄或 None。"""
    v = sl["cash"] + sl["qty"] * p
    cur = sl["qty"] * p / v if v else 0
    if not force and (abs(w - cur) < BAND and not (w == 0 and sl["qty"] > 0)):
        return None
    delta = w * v - sl["qty"] * p                # 正 = 要買的金額,負 = 要賣的金額
    if abs(delta) < 1e-9:
        return None
    if delta > 0:
        sl["cash"] -= delta; sl["qty"] += delta * (1 - FEE) / p
    else:
        sl["qty"] -= -delta / p; sl["cash"] += -delta * (1 - FEE)
    return {"side": "買" if delta > 0 else "賣", "price": p, "amount": round(abs(delta), 2), "to_pct": round(w * 100)}


def update(prof, rows_by_sym, L="load"):
    """把帳戶推進到最新一天;中間漏跑的日子會依序補上。回傳 (帳戶, 今天新發生的交易)。
    L 不給就從儲存層讀、跑完存回去;給 None 或帳戶 dict 則不讀不存(測試用)。"""
    syms = prof["symbols"]
    closes = {s: dict(rows_by_sym[s]) for s in syms}
    dates = sorted(set.intersection(*(set(closes[s]) for s in syms)))
    persist = L == "load"
    if persist:
        L = load()
    if L and (sorted(L["books"]["策略"]) != sorted(syms) or L["capital"] != prof["capital_usdt"]):
        raise ValueError("設定和模擬帳戶不一樣,要先重設帳戶")
    if not L:
        per = prof["capital_usdt"] / len(syms)
        L = {"version": VERSION, "strategy": strategy.NAME, "start": dates[-1], "capital": prof["capital_usdt"],
             "last": None, "halted": None,
             "books": {t: {s: {"cash": per, "qty": 0.0} for s in syms} for t in strategy.TRACKS},
             "trades": [], "history": []}
    new = []
    idx = {s: {d: i for i, (d, _) in enumerate(rows_by_sym[s])} for s in syms}
    cl = {s: [c for _, c in rows_by_sym[s]] for s in syms}
    for d in [x for x in dates if (x > L["last"] if L["last"] else x >= L["start"])]:
        px = {s: closes[s][d] for s in syms}
        first = not L["history"]
        for t, fn in strategy.TRACKS.items():
            if t == "策略" and L["halted"]:
                continue
            for s in syms:
                tr = _rebalance(L["books"][t][s], fn(cl[s], idx[s][d]), px[s], force=first)
                if tr and t == "策略":
                    tr.update(date=d, sym=s); L["trades"].append(tr); new.append(tr)
        eq = _value(L["books"]["策略"], px)
        if not L["halted"] and eq <= L.get("ref", L["capital"]) * (1 - prof["max_loss_pct"] / 100):
            for s in syms:
                tr = _rebalance(L["books"]["策略"][s], 0.0, px[s], force=True)
                if tr:
                    tr.update(date=d, sym=s, side="賣(觸發虧損上限)"); L["trades"].append(tr); new.append(tr)
            L["halted"] = {"date": d, "equity": round(_value(L["books"]["策略"], px), 2)}
        book = L["books"]["策略"]
        L["history"].append({"date": d, **{t: round(_value(L["books"][t], px), 2) for t in strategy.TRACKS},
                             "持有%": {s: round(book[s]["qty"] * px[s] / (book[s]["cash"] + book[s]["qty"] * px[s]) * 100)
                                       for s in syms}})
        L["last"] = d
    if persist:
        _save(L)
    return L, new


def summary(L):
    h = L["history"][-1]; cap = L["capital"]
    pct = lambda v: round((v / cap - 1) * 100, 2)
    return {"策略": L["strategy"], "開始日": L["start"], "本金USDT": round(cap),
            "目前總值USDT": round(h["策略"]), "損益%": pct(h["策略"]),
            "對照組_純50日均線損益%": pct(h["純50日均線"]), "對照組_買進持有損益%": pct(h["買進持有"]),
            "各幣持有比例%": h["持有%"], "交易次數": len(L["trades"]), "已跑天數": len(L["history"]),
            "是否暫停": f"已暫停({L['halted']['date']} 觸發虧損上限)" if L["halted"] else "否"}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--reset" in sys.argv:
        reset(); print("已清掉模擬帳戶"); sys.exit()
    if "--resume" in sys.argv:
        ref = resume()
        print("沒有暫停中的帳戶" if ref is None else f"已解除暫停,虧損上限改從目前總值 {ref} 起算"); sys.exit()
    prof = storage.load("profile.json")
    L, new = update(prof, {s: market.load(s) for s in prof["symbols"]})
    print(json.dumps(summary(L), ensure_ascii=False, indent=1)); print("新交易:", new)
