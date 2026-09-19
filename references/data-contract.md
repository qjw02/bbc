# 输入数据契约 · v1

每次分析一个 BTC 或 ETH 快照。可完整参考 `evals/fixtures/true_breakout.json`；它是合成测试快照。所有时间使用带时区 ISO 8601，推荐 UTC `Z`。JSON 数字必须有限，不接受 NaN/Infinity、字符串数字或布尔值冒充数字。

## 顶层

```json
{
  "symbol": "BTC",
  "as_of": "2026-09-18T12:00:00Z",
  "quote": {"price": 80000, "as_of": "2026-09-18T12:00:00Z", "source": "venue/symbol"},
  "candles": {"15m": [], "1H": [], "4H": []},
  "metrics": {},
  "previous_regime": "Neutral/Range"
}
```

以上只是字段示意，空 K 线不能生成信号。`previous_regime` 可省略；传入时必须是九个合法状态之一。as_of 是分析时点；引擎支持历史回放，不拿计算机当前时间覆盖它。要做实时分析，调用方必须使用真实当前 as_of，不能用旧时点假装最新报告。

quote 必须正数、有来源，默认距 as_of 不超过 120 秒，不能在未来。symbol 是资产，具体场所、币对、现货/合约、计价币种应写入 source 并保持一致。稳定币脱锚时不能把 USD 与 USDT 当成无风险等价价格。

## OHLCV

```json
{"close_time":"2026-09-18T12:00:00Z","open":80000,"high":80400,"low":79800,"close":80200,"volume":1000,"closed":true}
```

每个周期至少 30 根，严格递增、无重复和缺口；close_time 是 UTC 周期边界，4H 对齐 00/04/08/12/16/20 时。OHLC 正数且 low≤open/close≤high，volume≥0。未来或 `closed!=true` 的行不参与计算；过滤后仍必须连续且足够长。最后已收盘时间距 as_of 最多 1.5 个周期，用于容忍供数延迟；不能用大量未收盘 K 线凑足历史。

上游应从同一底层交易流聚合三周期并核对 OHLCV；v1 不自动跨周期重新聚合和纠错。修改时应保留原始数据以便复核。

## 观察值

```json
"funding_pct_8h": {
  "value": 0.01,
  "unit": "pct",
  "horizon": "8h_normalized",
  "observed_at": "2026-09-18T12:00:00Z",
  "available_at": "2026-09-18T12:00:00Z",
  "source": "exchange funding feed URL or vendor dataset id"
}
```

`observed_at` 是原始观察/统计期结束时间；`available_at` 是该版本数据实际发布、可被交易者获得的时间。必须 observed_at≤available_at≤as_of。修订数据使用修订发布时间，历史回放不能提前使用。最大年龄按 observed_at 计算；给旧数据打新 available_at 无法伪装新鲜。

所有支持字段、精确单位、窗口、时效、值域由 `config/defaults.json.metrics` 给出，是规范来源。不存在的字段会被忽略，不支持随意拼写别名；遗漏的字段在 rejected_metrics 中显示 missing。每个字段独立验证和过期，不用一个统一更新时间掩盖 ETF/债券发布时间差异。

- `pct`：百分数单位，例如价格变动 1 代表 1%；`pp`：百分点；`bp`：基点；百分数收益率 4.2 代表 4.2%。
- `USD_m`：百万美元；`USD_bn`：十亿美元；`flag` 只能 0/1；`index` 为指数点。
- horizon 严格区分 `spot`、`event`、`1h`、`4h`、`1d`、`24h`、`5d`、`7d`、`20d`、`1m`、`annualized`、`8h_normalized`。1d 指数据供应商的日窗口，24h 指滚动 24 小时，不能默默互换。
- OI、price、liquidations 的 1h 应对齐同一个已完成小时；`price_change_pct_1h` 应与该资产 1H 收盘计算一致。宏观引擎单独调用时消费上游已标准化变化；v1 不自动从历史宏观序列重建这些变化。
- JGB/UST 绝对水平与变化应同源、同时间；JPY IV 与期权 IV 提供相同定义期限的可比观察；期权 skew 是 put−call，term slope 是远期−近期。
- 标记为 event 的宏观、战争、MOF 和黑窗信息须由上游来源审核。无确认数据请省略，不把未知填成 0。示例里的零都是合成的明确无事件观察。

## 缺失与降级

关键项：UST2Y 日变化、实际收益率日变化、DXY 日变化、Nasdaq 日变化、VIX、USDJPY 1h、OI 1h、Funding、爆仓 z。任一不可用则 WAIT。总有效字段比例少于 55% 也 WAIT。其余缺失会降低覆盖并进入风险说明，不能解释为无风险；如果关键场景如日本冲击的数据源正在失效，使用 Skill 的分析者应进一步降级 WAIT。

## 输出

signal、plan、reasons、read_only、symbol、as_of 始终存在；通过基础输入检查后提供 structure、trends、macro。macro 返回主状态、并存状态、规则命中、覆盖、拒绝字段原因、有效数值和日本曲线/利差。计划 null 表示没有满足条件的分析机会；非 null 的 trigger 仍待后续数据确认。来源详情保留在原始输入，报告应引用输入 source 并区分观察时间与报告时间。

evals 使用共享完整 fixture + metrics 覆盖 + 具名价格变换；变换定义在 `tests/test_engines.py`，不是实时数据加载逻辑。合成场景测试是规则正确性检查，不是收益回测。
