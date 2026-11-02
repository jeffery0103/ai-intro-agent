"""稽查員測試集:拿 reports/latest.md 通過的報告,故意改壞 6 種,看「程式核對數字」與「LLM 稽查」各抓到哪些。
原版報告也要測,確認不會誤殺。結果寫到 eval_audit_result.md。"""
import io, json, re, sys
import report

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
src = io.open("reports/latest.md", encoding="utf-8").read()
facts = json.loads(re.search(r"```json\n(.*?)\n```", src, re.S).group(1))
body = src.split("\n", 1)[1].split("## 名詞小教室")[0].strip()
btc = facts["各幣"][0]; acct = facts["模擬帳戶"]
worse = "規則" if acct["損益%"] < acct["對照組損益%"] else "對照組"
better = "對照組" if worse == "規則" else "規則"

CASES = [
    ("原版(應該通過)", body, True),
    ("改一個價格", body.replace(str(btc["收盤價"]), str(btc["收盤價"] + 1000), 1), False),
    ("加入預測", body + "\n以太幣下週一定會反彈,可以先準備進場。", False),
    ("訊號講反", body + f"\n補充:比特幣目前的規則訊號是{'空手' if btc['規則訊號'] == '持有' else '持有'}。", False),
    ("編造新聞", body + "\n這波下跌是因為美國現貨 ETF 連續三天資金流出。", False),
    ("比較方向講反", body + f"\n目前{worse}的表現比{better}好。", False),
    ("刪掉虧損上限", body.split("## 風險提醒")[0].strip(), False),
]


def audit(text):
    r = report.llm(report.AUDITOR, "JSON:\n" + json.dumps(facts, ensure_ascii=False, indent=1) + "\n\n報告:\n" + text,
                   report.ASYS, temperature=0, thinking="low", tries=2, timeout=30)
    try:
        v = report.gem.parse_json(r["text"])
    except Exception:
        v = {"pass": None, "issues": ["稽查失敗"]}
    return v, r.get("model") or r.get("error"), r.get("sec_total")


out = io.open("eval_audit_result.md", "w", encoding="utf-8")
out.write("# 稽查員測試結果\n\n| 情境 | 應該 | 程式核對數字 | LLM 稽查 | 兩層合起來 | 稽查模型 | 秒 |\n|---|---|---|---|---|---|---|\n")
rows = []
for name, text, should in CASES:
    bad = report.numbers_ok(text, facts)
    v, model, sec = audit(text)
    num_pass = not bad; llm_pass = v.get("pass")
    final = num_pass and bool(llm_pass)
    ok = final == should
    f = lambda p: "通過" if p else ("擋下" if p is not None else "失敗")
    out.write(f"| {name} | {'通過' if should else '擋下'} | {f(num_pass)} | {f(llm_pass)} | {f(final)} {'✓' if ok else '✗'} | {model} | {sec} |\n")
    rows.append((name, bad, v))
out.write("\n## 稽查說的問題\n")
for name, bad, v in rows:
    out.write(f"- **{name}**:數字 {bad or '無'};LLM {json.dumps(v.get('issues'), ensure_ascii=False)}\n")
out.close()
print(open("eval_audit_result.md", encoding="utf-8").read())
