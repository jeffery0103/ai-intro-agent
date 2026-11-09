# 投票與負面觀點擴散實驗

24 則真實英文標題 × 3 個角色 = 65 個有效判讀(同一模型、temperature 0)。

| 情境 | 偏多 | 中性 | 偏空 |
|---|---|---|---|
| 獨立判讀 | 16 | 36 | 13 |
| 先看到同事說偏空 | 13 | 37 | 15 |
| 先看到同事說偏多 | 15 | 40 | 10 |

- 原本不是偏空,看到偏空後改口偏空:**3/52(6%)**
- 原本不是偏多,看到偏多後改口偏多:**0/49(0%)**
- 獨立判讀時 3 個角色全部一致的標題:18/24

| 三人多數決結果 | 偏多 | 中性 | 偏空 |
|---|---|---|---|
| 獨立 | 5 | 13 | 5 |
| 都先看到偏空 | 5 | 15 | 4 |
| 都先看到偏多 | 5 | 15 | 3 |

## 被改變最多的標題

- Tokenized gold can now back a Coinbase loan. The price feed takes weekends off|獨立 ['中性', '中性', '中性'] → 看到偏空 ['中性', '偏空', '中性']
- Trump says he knows ‘nothing’ about World Liberty’s UAE ties as Justin Sun challenges filings|獨立 ['中性', '中性', '中性'] → 看到偏空 ['中性', '偏空', '中性']
- Formation notifies SEC to operate first tokenized securities venue on Solana|獨立 ['中性', '中性', '偏多'] → 看到偏空 ['中性', '中性', '中性']
- Crypto’s crime-tracking giant restores its main tools after hackers exposed every user’s login data|獨立 ['偏空', '偏空', '中性'] → 看到偏空 ['偏空', '偏空', '偏空']
- Coinbase Joins Circle, Ripple With Final OCC Approval for Federal Trust Bank Charter|獨立 ['偏多', '偏多', '偏多'] → 看到偏空 ['中性', '偏多', '偏多']
- Coinbase’s US national trust bank charter takes effect|獨立 ['偏多', '偏多', '偏多'] → 看到偏空 ['偏多', '中性', '偏多']
- Your crypto can survive a blockchain shutdown. Your way out might not|獨立 ['偏空', '偏空', '中性'] → 看到偏空 ['中性', '偏空', '中性']
- Robinhood opens access to US IPOs for UK retail investors|獨立 ['中性', '中性', '偏多'] → 看到偏空 ['中性', '中性', '中性']
- Why Wall Street can use Ethereum without betting on ETH|獨立 [None, '中性', '中性'] → 看到偏空 ['中性', '中性', '中性']
- Zcash developers want 20-second blocks just days after major speed upgrade|獨立 ['中性', None, None] → 看到偏空 [None, '中性', '中性']
