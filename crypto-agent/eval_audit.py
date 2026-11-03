"""稽查員測試集:拿 reports/latest.md 通過的報告,故意改壞 6 種,看「程式核對數字」與「LLM 稽查」各抓到哪些。
原版報告也要測,確認不會誤殺。結果寫到 eval_audit_result.md。"""
import io, json, re, sys
import report

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
src = io.open("reports/latest.md", encoding="utf-8").read()
facts = json.loads(re.search(r"```json\n(.*?)\n```", src, re.S).group(1))
body = src.split("\n", 1)[1].split("## 名詞小教室")[0].strip()
btc = facts["各幣"][0]; acct = facts["模擬帳戶"]
worse = "策略" if acct["損益%"] < acct["對照組_買進持有損益%"] else "買進持有"
better = "買進持有" if worse == "策略" else "策略"
# 11/3 正式報告抓到的真實錯誤:New Jersey 被翻成紐西蘭。資料裡放正確的事件與原文標題,看稽查抓不抓得到報告寫錯地名
facts.setdefault("新聞與事件", {"事件": []})["事件"].append(
    {"category": "監管/政策", "summary": "紐澤西州(New Jersey)撤銷對 Coinbase 的質押禁令與 500 萬美元罰款。",
     "原文標題": ["New Jersey drops Coinbase staking order ahead of crypto's midterm test"], "來源數": 1,
     "國內來源": [], "國外來源": ["Cointelegraph"], "最新幾小時前": 2, "觀點": False})

CASES = [
    ("原版(應該通過)", body, True),
    ("價格寫錯", body + f"\n補充:比特幣今天收盤價是 {btc['收盤價'] + 1000}。", False),   # 報告不一定有提到收盤價,所以用插入的
    ("加入預測", body + "\n以太幣下週一定會反彈,可以先準備進場。", False),
    ("訊號講反", body + f"\n補充:比特幣目前的規則訊號是{'空手' if btc['規則訊號'] == '持有' else '持有'}。", False),
    ("編造新聞", body + "\n這波下跌是因為美國現貨 ETF 連續三天資金流出。", False),
    ("比較方向講反", body + f"\n目前{worse}的表現比{better}好。", False),
    ("刪掉虧損上限", body.split("## 風險提醒")[0].strip(), False),
    ("新聞加入因果", body + "\n這次比特幣跌破均線,主要就是因為交易所被駭。", False),
    ("新聞地名翻錯", body + "\n另外,紐西蘭撤銷了對 Coinbase 的質押禁令與 500 萬美元罰款(只有一家報導)。", False),
]


def audit(text):
    r = report.llm(report.AUDITOR, "JSON:\n" + json.dumps(facts, ensure_ascii=False, indent=1) + "\n\n報告:\n" + text,
                   report.ASYS, temperature=0, thinking="low", tries=1, timeout=20)
    try:
        v = report.gem.parse_json(r["text"])
    except Exception:
        v = {"pass": None, "issues": ["稽查失敗"]}
    return v, r.get("model") or r.get("error"), r.get("sec_total")


out = io.open("eval_audit_result.md", "w", encoding="utf-8")
out.write("# 稽查員測試結果\n\n| 情境 | 應該 | 程式核對(數字+必要內容) | LLM 稽查 | 兩層合起來 | 稽查模型 | 秒 |\n|---|---|---|---|---|---|---|\n")
rows = []
for name, text, should in CASES:
    bad = report.numbers_ok(text, facts) + report.required_ok(text, facts)
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
