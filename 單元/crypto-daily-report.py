import json, urllib.request, datetime as dt, time, io, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from crypto_gem import gemini
WRITER="gemini-flash-lite-latest"; AUDITOR="gemini-flash-latest"
trace=[]
def step(name, fn):
    t=time.time(); r=fn(); trace.append({"step":name,"sec":round(time.time()-t,1),**({k:r.get(k) for k in ("in","out","think","model")} if isinstance(r,dict) else {})}); return r
def fetch():
    k=json.load(urllib.request.urlopen("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=121",timeout=20))[:-1]
    f=json.load(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=3",timeout=20))
    return {"k":k,"f":f}
raw=step("1 抓資料(Binance 公開 API)",fetch)
def compute():
    c=[float(x[4]) for x in raw["k"]]; d=[dt.datetime.utcfromtimestamp(x[0]/1000).strftime('%Y-%m-%d') for x in raw["k"]]
    ma=lambda n,i=None: sum(c[(i if i is not None else len(c)-1)-n+1:(i if i is not None else len(c)-1)+1])/n
    g=l=0
    for j in range(len(c)-14,len(c)): ch=c[j]-c[j-1]; g+=max(ch,0); l+=max(-ch,0)
    rsi=100 if l==0 else 100-100/(1+g/l)
    rets=[c[i]/c[i-1]-1 for i in range(len(c)-30,len(c))]; vol=(sum(r*r for r in rets)/30)**0.5*100
    sig=[1 if c[i]>ma(50,i) else 0 for i in range(len(c)-60,len(c))]
    last_change=next((d[len(c)-60+i] for i in range(len(sig)-1,0,-1) if sig[i]!=sig[i-1]),"60 天內無變化")
    fr=sum(float(x["fundingRate"]) for x in raw["f"])/len(raw["f"])*100
    return {"日期":d[-1],"收盤價":round(c[-1]),"50日均線":round(ma(50)),"20日均線":round(ma(20)),"RSI14":round(rsi,1),
            "7日漲跌%":round((c[-1]/c[-8]-1)*100,1),"30日日波動度%":round(vol,2),"資金費率%(最近3期平均)":round(fr,4),
            "規則訊號":"持有(收盤價在50日均線上方)" if sig[-1] else "空手(收盤價在50日均線下方)","上次訊號改變日":last_change,
            "規則回測(2022-02~2026-11,含手續費0.1%)":"50日均線規則 +178.4%、最大回撤 -47.0%;買進持有 +95.3%、最大回撤 -66.7%;注意:過去表現不代表未來,參數敏感"}
data=step("2 算指標與規則訊號(程式,不用 LLM)",compute)
WSYS=("你是加密貨幣新手的每日報告助理。只能使用提供的 JSON 數據,不可編造任何數字或新聞。"
      "不可預測價格會漲或跌,不可使用『保證』『一定』『必漲』等字眼。進出場只能轉述『規則訊號』,並說明它是依 50 日均線的機械規則,不是預測。"
      "用繁體中文、300 字內,分成:今日概況、規則訊號、風險提醒三段。最後一行寫:『本報告為學習用途,不構成投資建議,是否交易由使用者自行決定。』")
rep=step("3 寫報告(LLM:"+WRITER+")",lambda: gemini(WRITER,"今日數據:\n"+json.dumps(data,ensure_ascii=False,indent=1),WSYS))
ASYS=("你是稽查員,負責檢查一份給新手的加密貨幣報告是否可以發送。逐條檢查:(1) 報告中的每個數字是否與 JSON 一致;(2) 是否出現價格預測或『保證/一定/必漲/必跌』等字眼;"
      "(3) 規則訊號是否與 JSON 相符;(4) 是否有風險提醒與免責聲明;(5) 是否編造 JSON 沒有的資訊(例如新聞)。"
      "只輸出 JSON:{\"pass\": true 或 false, \"issues\": [\"問題描述\", ...]}")
def audit(report): return gemini(AUDITOR,"JSON 數據:\n"+json.dumps(data,ensure_ascii=False)+"\n\n待檢查的報告:\n"+report,ASYS,temperature=0)
aud=step("4 稽查(LLM:"+AUDITOR+")",lambda: audit(rep.get("text","")))
bad=("今日比特幣收盤價為 95,000 美元,技術面強勢,明天保證上漲,建議立刻全倉買進!"
     "規則訊號:持有。風險:幾乎沒有風險。")
aud_bad=step("5 稽查測試:故意餵錯誤報告(LLM:"+AUDITOR+")",lambda: audit(bad))
out=io.open(f"report_{data['日期']}.md","w",encoding="utf-8")
out.write(f"# 加密貨幣每日報告 {data['日期']}\n\n## 數據(程式計算)\n```json\n{json.dumps(data,ensure_ascii=False,indent=1)}\n```\n\n## 報告({WRITER})\n{rep.get('text',rep)}\n\n## 稽查結果({AUDITOR})\n{aud.get('text',aud)}\n\n## 稽查測試:故意錯誤的報告\n> {bad}\n\n{aud_bad.get('text',aud_bad)}\n\n## Tracing\n| 步驟 | 秒 | 輸入 tokens | 輸出 tokens | 思考 tokens | 實際模型 |\n|---|---|---|---|---|---|\n")
for t in trace: out.write(f"| {t['step']} | {t['sec']} | {t.get('in') or '-'} | {t.get('out') or '-'} | {t.get('think') or '-'} | {t.get('model') or '-'} |\n")
out.close(); print("WROTE", f"report_{data['日期']}.md")
