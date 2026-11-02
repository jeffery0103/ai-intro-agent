import json, urllib.request, datetime as dt, time, io, collections
r=json.load(open('btc_1d.json'))
D=[(dt.datetime.utcfromtimestamp(x[0]/1000).strftime('%Y-%m-%d'), float(x[4]), float(x[5])) for x in r][:-1]
fr=collections.defaultdict(list)
for x in json.load(open('funding.json')):
    fr[dt.datetime.utcfromtimestamp(x['fundingTime']/1000).strftime('%Y-%m-%d')].append(float(x['fundingRate']))
closes=[c for _,c,_ in D]
def ma(i,n): return sum(closes[i-n+1:i+1])/n
def rsi(i,n=14):
    g=l=0
    for j in range(i-n+1,i+1):
        ch=closes[j]-closes[j-1]; g+=max(ch,0); l+=max(-ch,0)
    return 100 if l==0 else 100-100/(1+g/l)
N=40; W=90
out=io.open('eval2_result.txt','w',encoding='utf-8'); res=[]; tok=[]
for k in range(len(D)-N, len(D)):
    rows=[]
    for i in range(k-W,k):
        f=fr.get(D[i][0]); fs=f"{sum(f)/len(f)*100:.4f}%" if f else "NA"
        rows.append(f"{D[i][0]},{closes[i]:.0f},{D[i][2]:.0f},{ma(i,20):.0f},{ma(i,50):.0f},{rsi(i):.1f},{fs}")
    prompt=("以下是比特幣(BTC/USDT)過去 90 天的每日資料。欄位:日期,收盤價,成交量(BTC),20日均線,50日均線,RSI(14),永續合約平均資金費率\n"
            + "\n".join(rows) + f"\n\n請綜合價格趨勢、成交量、均線、RSI 與資金費率,預測 {D[k][0]} 的收盤價會比前一天上漲還是下跌。只回答一個字:「漲」或「跌」。")
    body=json.dumps({"model":"huihui_ai/qwen3-abliterated:30b","prompt":prompt,"stream":False,"think":False,
                     "options":{"temperature":0,"num_predict":5,"num_ctx":8192}}).encode()
    t=time.time()
    j=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/generate',data=body,headers={'Content-Type':'application/json'}),timeout=600))
    ans=j['response'].strip(); tok.append(j.get('prompt_eval_count'))
    pu='漲' in ans and '跌' not in ans; tu=closes[k]>closes[k-1]
    res.append((pu,tu)); out.write(f"{D[k][0]} 模型={ans!r} 實際={'漲' if tu else '跌'} ({time.time()-t:.1f}s, prompt {j.get('prompt_eval_count')} tokens)\n"); out.flush()
n=len(res); acc=sum(p==t for p,t in res)/n
out.write(f"\n測試天數 {n}\n模型準確率(90天+成交量+均線+RSI+資金費率) {acc:.1%}\n模型猜漲比例 {sum(p for p,_ in res)/n:.1%}\n平均 prompt tokens {sum(x for x in tok if x)/len(tok):.0f}\n")
out.close()
