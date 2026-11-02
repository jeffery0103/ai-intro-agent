# 加密貨幣每日報告 Agent

期末專題。給加密貨幣新手的每日報告:進出場訊號由**可回測的固定規則**產生,LLM 只負責用白話解釋,另一個 LLM 稽查,最後由使用者自己決定(Human-in-the-Loop)。**只用模擬資金,不下單、不碰交易所金鑰,不構成投資建議。**

## 上線策略:50 日均線 × 波動目標 30%(`strategy.py`)
- 收盤價在 50 日均線下方 → 持有 0%;上方 → 持有 min(1, 30% ÷ 最近 30 天年化波動)
- 怎麼選出來的(`lab/`):2019~2023 開發期挑策略與參數,2024 起期末考只考一次。期末考 BTC+ETH 各半:年化 +23%、最大回撤 -19%、夏普 1.07;買進持有 +12%、-60%、0.48(`lab/strategy_result.md`)
- 試過但沒採用:機器學習直接猜漲跌(8 組只有 1 組勉強超過雜訊,且照它交易輸買進持有,`lab/predict_result.md`)、大跌風險模型(AUC 0.50~0.55)、多均線投票
- 模擬帳戶同時記「策略」「純50日均線」「買進持有」三條路線,每天對帳

## 流程
```
設定 Agent(追問到變數填齊)→ state/profile.json(Memory)
                                   ↓
Binance 公開 API → 指標與規則訊號(程式)→ 模擬帳戶(跨天記憶,含對照組、虧損上限暫停)
                                   ↓
         回測 + 樣本外驗證 + 使用者上限的歷史機率(程式)
                                   ↓
   寫報告(Gemini Flash-Lite)→ 程式核對數字 → 稽查(Gemini Flash,失敗由 Flash-Lite 代打)
                                   ↓ 沒過就退回重寫一次
                     reports/日期.md(附名詞小教室、稽查結果、Tracing)
```

## 檔案
| 檔案 | 做什麼 |
|---|---|
| `profile_agent.py` | 設定 Agent:問本金、虧損上限、幣種;簡單回答由程式解析,其他才叫 LLM;一律經程式驗證 |
| `market.py` | 抓日線(快取在 `data/`)、算均線/RSI/波動、規則訊號 |
| `backtest.py` | 樣本外驗證(2018–2023 挑均線天數,2024 起測試)、一年內虧到上限的機率 |
| `sim.py` | 模擬帳戶:照訊號在收盤價買賣、手續費 0.1%、觸發上限全部賣出並暫停 |
| `report.py` | 每日報告主程式 |
| `gem.py` | Gemini API(金鑰只讀環境變數 `GEMINI_API_KEY`)、重試與代打 |
| `eval_profile.py` / `eval_audit.py` | 設定 Agent 與稽查員的測試集,結果在 `eval_*_result.md` |
| `run_daily.bat` | 給 Windows 工作排程器每天呼叫 |

## 部署(Render + UptimeRobot + Telegram)
- `server.py`:`GET /` 給 UptimeRobot 每 5 分鐘戳一次(免費方案不休眠),順便當時鐘:過了台灣 08:30 還沒發今天的報告就發;`POST /tg` 是 Telegram webhook。
- Render 免費方案硬碟會清空,設定與模擬帳戶存在私人 Gist(`storage.py`)。
- Render 設定:Root Directory `crypto-agent`、Build `pip install -r requirements.txt`、Start `python server.py`、區域選 Singapore 或 Frankfurt(避開 Binance 封鎖的美國)。
- 環境變數(在 Render 後台設定,不進 repo):`GEMINI_API_KEY`、`TELEGRAM_BOT_TOKEN`、`GIST_ID`、`GITHUB_TOKEN`(只要 Gist 權限)。
- Telegram 指令:`/report` `/status` `/terms` `/setup` `/resume` `/cancel`;第一個傳 `/start` 的人會被登記為擁有者,其他人會被拒絕。

## 使用
```
python profile_agent.py     第一次:回答設定問題
python report.py            產生今天的報告
python sim.py --resume      觸發虧損上限後,檢討完要繼續
python backtest.py BTC ETH  重跑回測
```
