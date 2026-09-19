# 流动性、资金流与衍生品

## 技术价格优先

扫单/假突破由价格影线和收盘代理识别，不宣称观察到全部止损单。冲高 + OI 增长 + 高正 funding 可能拥挤；跌破 + OI 下降 + 爆仓异常可能平仓驱动，不能仅由 OI 推断多空净方向。

OI 使用同一供应商、同一合约篮子且同一美元/币本位转换方法的百分比变动。Funding 统一为每 8 小时百分数，0.01 表示 0.01%，不是 1%；不同结算周期先归一化，不能直接混加。默认 OI 1h 增长 ≥5% 且同方向 funding 绝对值 ≥0.05% 时等待去拥挤。

爆仓提供 1h USD 百万美元总量与相对于过去至少 30 个可比小时的 z-score。基准只可用分析时点之前数据，标准差为零则应缺失并 WAIT。OI 下降 ≥6%、价格 1h 跌 ≥3%、爆仓 z≥3 同时满足为 Crypto-native Leverage Flush。任何最后一根 1H 涨跌超过 4% 也等待新平台，既不抄底也不追空。

## 期权

输入 ATM IV、25-delta put IV−call IV skew、远期减近期 ATM IV 的期限斜率、下次关键到期小时数、期权 OI 和有符号 gamma 估计。IV/skew 单位是百分数/百分点，不是小数。高 IV、期限倒挂、临近到期进入风险说明；方向不利 skew 是流量阻力之一。

Gamma 与 OI 在 v1 保留披露，不自动映射方向，因为交易商净仓方向、strike 和期限分布不可由总 OI 推断。Max pain 不是价格磁铁，不作为目标。上游有完整 strike/expiry 分布时可人工补充 pin/加速风险，但不能覆盖技术确认规则。

## ETF、稳定币、CME

ETF 为当前资产 BTC 或 ETH 的最新已完成交易日日净流量，百万美元；两者不能混用。稳定币 7 日供给变化、交易所余额变化和 Coinbase premium 作为资金背景。增发不是已流入风险资产，不能单独产生 LONG。

CME 提供年化期现基差与日 OI 变化；负基差/持仓急减可成为风险阻力，正基差也不等同机构做多，因为可能是 cash-and-carry 对冲。默认反方向 ETF、稳定币、CME 基差，加上方向不利 skew 或 CME OI 急降，累计至少三个阻力则 WAIT；少于三个写入 main_risk。

慢数据按自身周期使用：ETF 最大 120h、CME 96h，周末沿用已发布数据时明确标为旧观察，不把未公布日流量填为零。配置中的宽限不是交易日历；节假日超时会降级，供应商适配器需要补日历和交易时段。

来源参考：[CME cryptocurrency data](https://www.cmegroup.com/market-data/browse-data/cryptocurrency-data.html)、[CME basis tool](https://www.cmegroup.com/markets/cryptocurrencies/cryptocurrency-basis-watch-and-implied-rate-tool)。ETF 与稳定币优先基金/发行方披露，衍生品使用交易所或明确标注覆盖面的聚合商。v1 不内置这些源的下载接口。
