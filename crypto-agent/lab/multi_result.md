# 多模型投票實驗

24 則真實英文標題,7 個模型。

## 各模型判讀與被帶走的比例

| 模型 | 有效(獨立/偏空/偏多) | 獨立判讀 偏多/中性/偏空 | 看到偏空後,原本不是偏空的改口 | 看到偏多後,原本不是偏多的改口 |
|---|---|---|---|---|
| claude-haiku | 24/24/24 | 4/16/4 | 0/20(0%) | 0/20(0%) |
| claude-opus | 24/24/24 | 6/15/3 | 0/21(0%) | 0/18(0%) |
| claude-sonnet | 24/24/24 | 6/12/6 | 1/18(6%) | 0/18(0%) |
| gemini-3.1-flash-lite | 24/24/22 | 8/12/4 | 1/20(5%) | 1/15(7%) |
| gemini-flash-lite-latest | 18/22/24 | 3/13/2 | 0/15(0%) | 0/15(0%) |
| gemma3-4b | 24/24/24 | 3/14/7 | 1/17(6%) | 10/21(48%) |
| qwen3-8b | 24/24/24 | 13/3/8 | 7/16(44%) | 3/11(27%) |
| **合計** | | | **10/127(8%)** | **14/118(12%)** |

## 多數決

獨立判讀時所有模型完全一致的標題:**7/24**。

| 多數決結果 | 偏多 | 中性 | 偏空 |
|---|---|---|---|
| 獨立 | 6 | 14 | 4 |
| 看到偏空 | 6 | 14 | 4 |
| 看到偏多 | 7 | 13 | 4 |

多數決被帶走的標題:看到偏空 **0/24**、看到偏多 **1/24**。

## 逐則(獨立判讀)

| 標題 | claude-haiku | claude-opus | claude-sonnet | gemini-3.1-flash-lite | gemini-flash-lite-latest | gemma3-4b | qwen3-8b |
|---|---|---|---|---|---|---|---|
| NYSE picks Avalanche to settle tokenized stocks amid Wall Street's blo | 中性 | 偏多 | 偏多 | 偏多 | 中性 | 中性 | 偏多 |
| Here’s what happened in crypto today | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 |
| The $2.85B Binance hackers lost shows why the UK needs stablecoin free | 偏空 | 中性 | 中性 | 中性 | 中性 | 偏空 | 偏空 |
| Strategy buys 1,036 Bitcoin as BTC holdings climb to 850,364 | 偏多 | 偏多 | 偏多 | 偏多 | 偏多 | 偏多 | 偏多 |
| Strategy Buys $82M in Bitcoin, Buys Back $188M of STRC | 偏多 | 偏多 | 偏多 | 偏多 | 偏多 | 中性 | 偏多 |
| Jito’s Solana data feed puts a price on seeing trades early | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 偏多 |
| ‘Connecting the dots’: Michael Saylor’s Strategy buys another 1,036 bi | 偏多 | 偏多 | 偏多 | 偏多 | None | 偏多 | 偏多 |
| Bitcoin loses 50-week moving average as 24-hour crypto long liquidatio | 偏空 | 偏空 | 偏空 | 偏空 | None | 偏空 | 偏空 |
| Microsoft-Backed Space and Time Launches Platform to Let AI Agents Ver | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 偏多 |
| Solana set for its first tokenized stock venue under SEC framework, li | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 偏多 |
| Tokenized gold can now back a Coinbase loan. The price feed takes week | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 偏多 |
| Trump says he knows ‘nothing’ about World Liberty’s UAE ties as Justin | 中性 | 中性 | 偏空 | 中性 | 中性 | 中性 | 中性 |
| Bitcoin bulls can't rely on ETF flows | 偏空 | 偏空 | 偏空 | 偏空 | 偏空 | 偏空 | 偏空 |
| Formation notifies SEC to operate first tokenized securities venue on  | 中性 | 中性 | 中性 | 偏多 | 偏多 | 中性 | 偏多 |
| EU taps industry to set standards for tokenized securities | 中性 | 中性 | 中性 | 偏多 | 中性 | 中性 | 偏多 |
| Crypto’s crime-tracking giant restores its main tools after hackers ex | 中性 | 中性 | 偏空 | 偏空 | 偏空 | 偏空 | 偏空 |
| Coinbase Joins Circle, Ripple With Final OCC Approval for Federal Trus | 偏多 | 偏多 | 偏多 | 偏多 | None | 中性 | 偏多 |
| Nvidia-led tech selloff weighs on crypto majors | 偏空 | 偏空 | 偏空 | 偏空 | None | 偏空 | 偏空 |
| Coinbase’s US national trust bank charter takes effect | 中性 | 偏多 | 偏多 | 偏多 | None | 偏多 | 偏多 |
| Your crypto can survive a blockchain shutdown. Your way out might not | 中性 | 中性 | 中性 | 中性 | None | 偏空 | 偏多 |
| Trump Says He Knows 'Nothing' About World Liberty Financial as He Defe | 中性 | 中性 | 偏空 | 中性 | 中性 | 中性 | 偏空 |
| Robinhood opens access to US IPOs for UK retail investors | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 |
| Why Wall Street can use Ethereum without betting on ETH | 中性 | 中性 | 中性 | 中性 | 中性 | 中性 | 偏空 |
| Zcash developers want 20-second blocks just days after major speed upg | 中性 | 中性 | 中性 | 中性 | 中性 | 偏空 | 偏空 |
