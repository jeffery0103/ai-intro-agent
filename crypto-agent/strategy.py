"""上線用的策略(純 Python,Render 上不需要 sklearn)。
由 lab/strategy_lab.py 選出:開發期 2019~2023 兩幣平均夏普最高,2024 起的期末考也贏過買進持有。
- 收盤價在 50 日均線下方 → 持有 0%
- 在上方 → 持有比例 = min(1, 目標年化波動 30% ÷ 最近 30 天年化波動):市場越瘋買越少"""
import math
import market

NAME = "50日均線×波動目標30%"
MA_N, TARGET_VOL, VOL_N = 50, 0.30, 30


def vol(c, i, n=VOL_N):
    r = [c[j] / c[j - 1] - 1 for j in range(i - n + 1, i + 1)]
    m = sum(r) / n
    return math.sqrt(sum((x - m) ** 2 for x in r) / n) * math.sqrt(365)


def weight(c, i):
    if c[i] <= market.ma(c, i, MA_N):
        return 0.0
    return min(1.0, TARGET_VOL / vol(c, i))


def ma50(c, i):
    return float(market.signal(c, i, MA_N))


def hold(c, i):
    return 1.0


TRACKS = {"策略": weight, "純50日均線": ma50, "買進持有": hold}     # 模擬帳戶同時記這三條
