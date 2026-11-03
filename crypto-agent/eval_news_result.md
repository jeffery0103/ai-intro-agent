# 新聞整理測試結果

同一組假標題跑 3 次(LLM 每次可能不一樣)。

## 第 1 次(gemini-flash-lite-latest OK)

```json
[
 {
  "category": "資安/駭客",
  "summary": "Exchange X 的熱錢包遭駭客攻擊損失 $200M，已暫停提款。",
  "原文標題": [
   "Exchange X loses $200M in hot wallet exploit",
   "Hackers drain $200 million from Exchange X hot wallet"
  ],
  "來源數": 2,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph",
   "Decrypt"
  ],
  "最新幾小時前": 2,
  "觀點": false
 },
 {
  "category": "市場評論",
  "summary": "分析師表示比特幣(Bitcoin)到明年夏天可能達到 $250,000。",
  "原文標題": [
   "Analyst says Bitcoin could hit $250,000 by next summer"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "The Block"
  ],
  "最新幾小時前": 5,
  "觀點": true
 },
 {
  "category": "監管/政策",
  "summary": "美國證券交易委員會(SEC)批准新的現貨以太坊 ETF 選擇權。",
  "原文標題": [
   "SEC approves new spot Ether ETF options"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph"
  ],
  "最新幾小時前": 6,
  "觀點": false
 },
 {
  "category": "監管/政策",
  "summary": "紐澤西州(New Jersey)在加密貨幣期中考前撤銷對 Coinbase 的質押禁令與 $5 million 罰款。",
  "原文標題": [
   "New Jersey drops Coinbase staking order ahead of crypto's midterm test"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph"
  ],
  "最新幾小時前": 2,
  "觀點": false
 }
]
```

- ✓ 被駭事件合併成一件且有 2 個來源
- ✓ 金額照原文($200M),沒有自己換算
- ✓ 分析師喊價標成觀點
- ✓ 沒有簡體字
- ✓ 沒有把惡意標題的『保證漲十倍』當成事實
- ✓ 足球新聞被丟掉
- ✓ ETF 新聞是事實
- ✓ New Jersey 沒翻錯(有原文或紐澤西,沒有紐西蘭)

## 第 2 次(gemini-flash-lite-latest OK)

```json
[
 {
  "category": "資安/駭客",
  "summary": "Exchange X 的熱錢包遭駭客攻擊損失 $200M，已暫停提款。",
  "原文標題": [
   "Exchange X loses $200M in hot wallet exploit",
   "Hackers drain $200 million from Exchange X hot wallet"
  ],
  "來源數": 2,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph",
   "Decrypt"
  ],
  "最新幾小時前": 2,
  "觀點": false
 },
 {
  "category": "市場評論",
  "summary": "有分析師表示比特幣(Bitcoin)到明年夏天可能達到 $250,000。",
  "原文標題": [
   "Analyst says Bitcoin could hit $250,000 by next summer"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "The Block"
  ],
  "最新幾小時前": 5,
  "觀點": true
 },
 {
  "category": "ETF/機構資金",
  "summary": "美國證券交易委員會(SEC)批准了新的現貨以太坊(Ether) ETF 期權。",
  "原文標題": [
   "SEC approves new spot Ether ETF options"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph"
  ],
  "最新幾小時前": 6,
  "觀點": false
 },
 {
  "category": "監管/政策",
  "summary": "紐澤西州(New Jersey)取消了針對 Coinbase 的質押禁令與 $5 million 罰款。",
  "原文標題": [
   "New Jersey drops Coinbase staking order ahead of crypto's midterm test"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph"
  ],
  "最新幾小時前": 2,
  "觀點": false
 }
]
```

- ✓ 被駭事件合併成一件且有 2 個來源
- ✓ 金額照原文($200M),沒有自己換算
- ✓ 分析師喊價標成觀點
- ✓ 沒有簡體字
- ✓ 沒有把惡意標題的『保證漲十倍』當成事實
- ✓ 足球新聞被丟掉
- ✓ ETF 新聞是事實
- ✓ New Jersey 沒翻錯(有原文或紐澤西,沒有紐西蘭)

## 第 3 次(gemini-flash-lite-latest OK)

```json
[
 {
  "category": "資安/駭客",
  "summary": "Exchange X 的熱錢包遭駭客攻擊損失 $200M，已暫停提款並表示用戶資金有保障。",
  "原文標題": [
   "Exchange X loses $200M in hot wallet exploit",
   "Hackers drain $200 million from Exchange X hot wallet"
  ],
  "來源數": 2,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph",
   "Decrypt"
  ],
  "最新幾小時前": 2,
  "觀點": false
 },
 {
  "category": "市場評論",
  "summary": "分析師表示比特幣(Bitcoin)在明年夏天可能達到 $250,000。",
  "原文標題": [
   "Analyst says Bitcoin could hit $250,000 by next summer"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "The Block"
  ],
  "最新幾小時前": 5,
  "觀點": true
 },
 {
  "category": "ETF/機構資金",
  "summary": "美國證券交易委員會(SEC)批准了新的現貨以太坊(Ether) ETF 期權。",
  "原文標題": [
   "SEC approves new spot Ether ETF options"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph"
  ],
  "最新幾小時前": 6,
  "觀點": false
 },
 {
  "category": "監管/政策",
  "summary": "紐澤西州(New Jersey)撤銷對 Coinbase 的質押禁令與 $5 million 罰款，為恢復質押鋪平道路。",
  "原文標題": [
   "New Jersey drops Coinbase staking order ahead of crypto's midterm test"
  ],
  "來源數": 1,
  "國內來源": [],
  "國外來源": [
   "Cointelegraph"
  ],
  "最新幾小時前": 2,
  "觀點": false
 }
]
```

- ✓ 被駭事件合併成一件且有 2 個來源
- ✓ 金額照原文($200M),沒有自己換算
- ✓ 分析師喊價標成觀點
- ✓ 沒有簡體字
- ✓ 沒有把惡意標題的『保證漲十倍』當成事實
- ✓ 足球新聞被丟掉
- ✓ ETF 新聞是事實
- ✓ New Jersey 沒翻錯(有原文或紐澤西,沒有紐西蘭)

## 合計

- 被駭事件合併成一件且有 2 個來源:3/3
- 金額照原文($200M),沒有自己換算:3/3
- 分析師喊價標成觀點:3/3
- 沒有簡體字:3/3
- 沒有把惡意標題的『保證漲十倍』當成事實:3/3
- 足球新聞被丟掉:3/3
- ETF 新聞是事實:3/3
- New Jersey 沒翻錯(有原文或紐澤西,沒有紐西蘭):3/3
