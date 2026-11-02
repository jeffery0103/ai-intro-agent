"""模擬帳戶(跨天的記憶):資金平分給每個幣,照規則訊號在收盤價假裝買賣,含手續費。
同時記一個「第一天就買進、之後都不動」的對照組。總值低於本金 ×(1−上限)就全部賣出並暫停,
等使用者檢討後用 --resume 繼續(Human-in-the-Loop)。
用法:python sim.py            更新到最新收盤
      python sim.py --resume   解除暫停
      python sim.py --reset    清掉帳戶重新開始"""
import json, sys
import market, storage

FEE = 0.001
NAME = "ledger.json"


def load():
    return storage.load(NAME)


def _save(L):
    storage.save(NAME, L)


def reset():
    storage.delete(NAME)


def resume():
    """解除暫停;之後的虧損上限從目前總值重新算。"""
    L = load()
    if not L or not L["halted"]:
        return None
    L["ref"] = L["history"][-1]["equity"]; L["halted"] = None; _save(L)
    return L["ref"]


def value(L, px):
    return sum(s["cash"] + s["qty"] * px[k] for k, s in L["sleeves"].items())


def update(prof, rows_by_sym, n=50, L="load"):
    """把帳戶推進到最新一天;中間漏跑的日子會依序補上。回傳 (帳戶, 今天新發生的交易)。
    L 不給就從儲存層讀、跑完存回去;給 None 或帳戶 dict 則不讀不存(測試用)。"""
    syms = prof["symbols"]
    closes = {s: dict(rows_by_sym[s]) for s in syms}
    dates = sorted(set.intersection(*(set(closes[s]) for s in syms)))
    persist = L == "load"
    if persist:
        L = load()
    if L and (sorted(L["sleeves"]) != sorted(syms) or L["capital"] != prof["capital_usdt"]):
        raise ValueError("設定和模擬帳戶不一樣,要先重設帳戶")
    if not L:
        start = dates[-1]; per = prof["capital_usdt"] / len(syms)
        L = {"start": start, "capital": prof["capital_usdt"], "ma": n, "last": None, "halted": None,
             "sleeves": {s: {"cash": per, "qty": 0.0} for s in syms},
             "benchmark": {s: per * (1 - FEE) / closes[s][start] for s in syms},
             "trades": [], "history": []}
    new = []
    idx = {s: [d for d, _ in rows_by_sym[s]] for s in syms}
    cl = {s: [c for _, c in rows_by_sym[s]] for s in syms}
    for d in [x for x in dates if (x > L["last"] if L["last"] else x >= L["start"])]:
        px = {s: closes[s][d] for s in syms}
        if not L["halted"]:
            for s in syms:
                i = idx[s].index(d); want = market.signal(cl[s], i, L["ma"]); sl = L["sleeves"][s]
                if want and sl["qty"] == 0:
                    q = sl["cash"] * (1 - FEE) / px[s]
                    t = {"date": d, "sym": s, "side": "買", "price": px[s], "qty": q, "fee": sl["cash"] * FEE}
                    sl["qty"], sl["cash"] = q, 0.0
                elif not want and sl["qty"] > 0:
                    gross = sl["qty"] * px[s]
                    t = {"date": d, "sym": s, "side": "賣", "price": px[s], "qty": sl["qty"], "fee": gross * FEE}
                    sl["cash"], sl["qty"] = gross * (1 - FEE), 0.0
                else:
                    continue
                L["trades"].append(t); new.append(t)
        eq = value(L, px)
        if not L["halted"] and eq <= L.get("ref", L["capital"]) * (1 - prof["max_loss_pct"] / 100):
            for s, sl in L["sleeves"].items():
                if sl["qty"] > 0:
                    gross = sl["qty"] * px[s]
                    t = {"date": d, "sym": s, "side": "賣(觸發虧損上限)", "price": px[s], "qty": sl["qty"], "fee": gross * FEE}
                    sl["cash"], sl["qty"] = gross * (1 - FEE), 0.0
                    L["trades"].append(t); new.append(t)
            eq = value(L, px)
            L["halted"] = {"date": d, "equity": round(eq, 2)}
        bh = sum(L["benchmark"][s] * px[s] for s in syms)
        L["history"].append({"date": d, "equity": round(eq, 2), "benchmark": round(bh, 2)})
        L["last"] = d
    if persist:
        _save(L)
    return L, new


def summary(L):
    h = L["history"][-1]; cap = L["capital"]
    pos = {s: ("持有" if sl["qty"] > 0 else "空手") for s, sl in L["sleeves"].items()}
    return {"開始日": L["start"], "本金USDT": round(cap), "目前總值USDT": round(h["equity"]),
            "損益%": round((h["equity"] / cap - 1) * 100, 2),
            "對照組(第一天買進不動)總值USDT": round(h["benchmark"]),
            "對照組損益%": round((h["benchmark"] / cap - 1) * 100, 2),
            "各幣狀態": pos, "交易次數": len(L["trades"]), "已跑天數": len(L["history"]),
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
