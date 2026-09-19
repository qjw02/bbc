# 日本与 Carry Trade Unwind

## 必备观察面

BOJ 政策/指引；JGB2Y、10Y、30Y、40Y 绝对收益率及日变动；UST2Y−JGB2Y、UST10Y−JGB10Y；USDJPY 1h/4h 变动；JPY 隐含波动率及日变动；Nikkei/TOPIX；MOF 干预和 Rate-check。

绝对收益率以百分数输入，例如 1.2 表示 1.2%；引擎计算利差和 2s10s/10s30s/30s40s JGB 曲线时乘 100 转为 bp。美日利差变化支持 1h、4h、24h、5d、20d：上游须按同一时间戳计算 `(UST_t-JGB_t)-(UST_old-JGB_old)` 再乘 100。长窗口用于上下文，当前检测重点使用 1h/4h 压缩速度。不能用不同交易日的收益率拼成盘中压缩。

## 默认触发链

1. USDJPY 1h 跌幅至少 0.7% 或 4h 跌幅至少 1.2%，即日元快速升值。
2. 至少两项：JGB10Y/30Y/40Y 快升、美日利差快速压缩、JPY IV 快升、BOJ 鹰派。阈值见配置。
3. 至少两项：Nikkei/TOPIX/Nasdaq 下跌，Crypto OI 减少，Crypto 价格下跌。

三层同时满足，才标记 Carry Trade Unwind。Nikkei/TOPIX 高度相关、多个期限 JGB 也相关；这是保守警报分类，不宣称独立因子概率。输出 funding_evidence、contagion_evidence 和 yen_appreciation 供复核。BTC/ETH 1H 破位仍由技术层判断。

JGB 收益率上升但 USDJPY 上涨，不能触发此状态。只有日元升值而无融资压力/风险传染，也不能确认为 unwind。套息冲击时不机械接多；顺势做空仍须等待反弹、结构和盈亏比条件，瀑布段不能追空。

MOF Rate-check 与实际干预分开存储。任一有效告警会进入计划 main_risk，但不会单独生成方向或确认 unwind。未证实传闻不写成 `mof_intervention=1`；保留在人工说明中并根据不确定性选择 WAIT。

## 来源

[BOJ monetary policy](https://www.boj.or.jp/en/mopo/) 用于政策和声明；[BOJ statistics](https://www.stat-search.boj.or.jp/) 用于统计查询；[MOF intervention operations](https://www.mof.go.jp/english/policy/international_policy/reference/feio/index.html) 用于正式外汇干预记录。正式干预披露可能滞后，不能在历史回放中使用后来发布的确认信息。
