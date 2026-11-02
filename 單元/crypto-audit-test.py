import os, sys, json, time; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypto_gem import gemini
data={"日期":"2026-11-01","收盤價":78354,"50日均線":81982,"20日均線":80936,"RSI14":34.9,"7日漲跌%":-2.2,"30日日波動度%":1.47,"資金費率%(最近3期平均)":0.0096,"規則訊號":"空手(收盤價在50日均線下方)","上次訊號改變日":"2026-10-22"}
ASYS=("你是稽查員,負責檢查一份給新手的加密貨幣報告是否可以發送。逐條檢查:(1) 報告中的每個數字是否與 JSON 一致;(2) 是否出現價格預測或『保證/一定/必漲/必跌』等字眼;"
      "(3) 規則訊號是否與 JSON 相符;(4) 是否有風險提醒與免責聲明;(5) 是否編造 JSON 沒有的資訊(例如新聞)。只輸出 JSON:{\"pass\": true 或 false, \"issues\": [\"問題描述\", ...]}")
bad="今日比特幣收盤價為 95,000 美元,技術面強勢,明天保證上漲,建議立刻全倉買進!規則訊號:持有。風險:幾乎沒有風險。"
def audit_with_fallback(report, models=("gemini-flash-latest","gemini-flash-lite-latest"), tries=3):
    log=[]
    for m in models:
        for i in range(tries):
            r=gemini(m,"JSON 數據:\n"+json.dumps(data,ensure_ascii=False)+"\n\n待檢查的報告:\n"+report,ASYS,temperature=0)
            log.append(f"{m} 第{i+1}次: {'成功' if 'text' in r else r.get('error')} ({r.get('sec')}s)")
            if 'text' in r: return r, log
            time.sleep(5*(i+1))
    return None, log
r,log=audit_with_fallback(bad)
print("\n".join(log)); print(r and r["text"]); print(r and {k:r.get(k) for k in ("model","sec","in","out","think")})
