import json, datetime as dt, io
r=json.load(open('btc_1d.json'))
D=[(dt.datetime.utcfromtimestamp(x[0]/1000).strftime('%Y-%m-%d'), float(x[4])) for x in r][:-1]
c=[x[1] for x in D]
def run(sig_fn, start, fee=0.001):
    eq=1.0; peak=1.0; mdd=0; pos=0; trades=0; inmkt=0; curve=[]
    for i in range(start, len(c)):
        want=sig_fn(i-1)  # decide using data up to yesterday
        if want!=pos: eq*=1-fee; trades+=1; pos=want
        if pos: eq*=c[i]/c[i-1]; inmkt+=1
        peak=max(peak,eq); mdd=min(mdd,eq/peak-1); curve.append(eq)
    return eq-1, mdd, trades, inmkt/(len(c)-start)
ma=lambda i,n: sum(c[i-n+1:i+1])/n
S=50
res={
 '買進持有':run(lambda i:1, S),
 '50日均線(在均線上才持有)':run(lambda i: 1 if c[i]>ma(i,50) else 0, S),
 '20/50日均線交叉':run(lambda i: 1 if ma(i,20)>ma(i,50) else 0, S),
}
out=io.open('backtest_result.txt','w',encoding='utf-8')
out.write(f"回測期間 {D[S][0]} ~ {D[-1][0]}(日線收盤,手續費每次 0.1%)\n")
for k,(ret,mdd,tr,im) in res.items():
    out.write(f"{k}: 總報酬 {ret:+.1%} | 最大回撤 {mdd:.1%} | 買賣次數 {tr} | 持有時間 {im:.0%}\n")
out.close()
