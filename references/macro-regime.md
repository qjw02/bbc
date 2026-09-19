# 宏观状态引擎

## 输入与证据

美国：Fed 政策/讲话鹰派事件、UST2Y/10Y 绝对收益率和日变动、10Y TIPS 实际收益率、DXY、Nasdaq/S&P、VIX/MOVE、HY/IG 信用利差、黄金、油价及战争风险。CPI/PCE/就业等数据的实际值、预期差由上游整理为有来源的事件，结合债券/美元/股指的实际反应；不能只凭新闻标题判断方向。

流动性：Fed 资产、TGA、RRP 周变化，US/全球 M2 月变化；ETF 日净流量、稳定币供给。M2、收益率绝对水平、信用利差绝对水平主要作背景披露，不把低频序列变化当作 15m 触发器。Fed 资产增加、TGA/RRP 减少仅为本版流动性代理，不能解释为恒定等额资金进入 BTC。

每个指标必须提供 value/unit/horizon/observed_at/available_at/source。先过滤未来、过期、单位错误和来源缺失的值，再计算命中，缺失不会转为零证据。关键指标缺失或总体覆盖少于 55% 时 WAIT。覆盖比例是数量占比，不是置信概率，也不保证某模块全覆盖。

## 九种状态

具体数值在 `config/defaults.json`，调整时应保留单位并做历史验证。默认逻辑：

- **Liquidity Risk-On**：Fed/TGA/RRP、稳定币、ETF、美元六项至少四项支持，且稳定币增长必需。
- **Normal Risk-On**：美股走强、VIX 温和、美元/实际利率不强等至少三项，Nasdaq 走强必需。
- **Neutral/Range**：其余状态条件均未满足；不等同确认风险不存在。
- **Inflation Shock**：油价、名义/实际收益率上涨和 Nasdaq 下跌至少三项。
- **Fed Tightening Shock**：Fed 鹰派、UST2Y 上涨、实际利率上涨、美元上涨至少三项，UST2Y 上涨必需。
- **Carry Trade Unwind**：日元快速升值 AND 至少两项融资压力 AND 至少两项风险资产/杠杆传染；见日本模块。
- **Credit Stress**：HY 扩大必需，且 HY/IG/VIX/MOVE 至少三项压力。
- **War/Oil Shock**：有来源的战争风险 AND 油价急涨；黄金是可选佐证。
- **Crypto-native Leverage Flush**：价格快速下跌 AND OI 明显减少 AND 爆仓异常。

同一快照可多状态共存。主状态按 Credit > Carry > War/Oil > Fed > Inflation > Crypto Flush > Liquidity Risk-On > Normal Risk-On 排序，未命中为 Neutral。并存列表用于避免主状态掩盖独立的去杠杆禁入条件。这里是可解释规则的优先级，不是综合分数模型。

传入合法 `previous_regime` 可获得 changed；v1 无持续状态、滞后确认和持仓记忆，每次重新计算。风险状态可以限制做多，但不能单独生成做空：价格结构、位置和确认仍须通过。宏观利空但价格向上突破时 WAIT 并解释拒跌，不推导必然上涨。

## 来源与更新

优先使用 [Federal Reserve](https://www.federalreserve.gov/monetarypolicy.htm) 和 [H.4.1](https://www.federalreserve.gov/releases/h41/) 核对政策与资产负债表；收益率采用 [US Treasury rates](https://home.treasury.gov/resource-center-data-chart-center/interest-rates)；事件与行情需记录实际供应商和发布时间。官方数据用于定义和核对来源，本项目阈值是独立设计。
