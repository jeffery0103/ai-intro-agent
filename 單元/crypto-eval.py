import json, urllib.request, datetime as dt, time, io
r=json.load(open('btc_1d.json'))
d=[(dt.datetime.utcfromtimestamp(x[0]/1000).strftime('%Y-%m-%d'), float(x[4])) for x in r]
d=d[:-1]  # drop today's unfinished candle
N=40; W=30
out=io.open('eval_result.txt','w',encoding='utf-8')
res=[]
for k in range(len(d)-N, len(d)):
    hist=d[k-W:k]; target_up = d[k][1] > d[k-1][1]
    prompt=("以下是比特幣(BTC/USDT)過去 30 天每日收盤價(美元):\n" + "\n".join(f"{a},{b:.0f}" for a,b in hist) +
            f"\n\n請預測 {d[k][0]} 的收盤價會比前一天上漲還是下跌。只回答一個字:「漲」或「跌」。")
    body=json.dumps({"model":"huihui_ai/qwen3-abliterated:30b","prompt":prompt,"stream":False,"think":False,
                     "options":{"temperature":0,"num_predict":5,"num_ctx":4096}}).encode()
    t=time.time()
    ans=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/generate',data=body,headers={'Content-Type':'application/json'}),timeout=600))['response'].strip()
    pred_up = '漲' in ans and '跌' not in ans
    prev_up = d[k-1][1] > d[k-2][1]
    res.append((d[k][0], ans, pred_up, target_up, prev_up))
    out.write(f"{d[k][0]} 模型={ans!r} 實際={'漲' if target_up else '跌'} ({time.time()-t:.1f}s)\n"); out.flush()
n=len(res)
acc=sum(p==t for _,_,p,t,_ in res)/n
up=sum(t for *_,t,_ in res)/n
same=sum(pv==t for *_,t,pv in res)/n
pu=sum(p for _,_,p,_,_ in res)/n
out.write(f"\n測試天數 {n}\n模型準確率 {acc:.1%}\n永遠猜漲 {up:.1%}\n照抄昨天 {same:.1%}\n模型猜漲的比例 {pu:.1%}\n")
out.close()
