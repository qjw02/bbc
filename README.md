# BTC/ETH Macro Trading Skill · v0.1

只读 BTC/ETH 技术结构 + 宏观状态分析。顺势、回踩接多、反弹接空，宁可错过，不追价。支持动态关键位、已收盘 15m/1H/4H、假突破/流动性扫单、美国宏观、日本套息、加密资金与杠杆风险。

输出限定 `LONG BIAS`、`SHORT BIAS`、`WAIT`、`STRUCTURE CHANGE`。只有通过位置、趋势、确认、数据质量和扣费后盈亏比门槛才产生一个条件入场计划。无交易 API、密钥需求、自动下单或联网副作用。

## 快速运行

Python 3.10 或以上，无第三方依赖。在仓库根目录执行：

```sh
python -m scripts.signal_engine evals/fixtures/true_breakout.json
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

示例全部是合成历史测试数据，不代表当前价格或当前宏观状态。真实分析需自行从可信数据商采集、归一化，保存为相同 JSON 格式：

```sh
python -m scripts.signal_engine snapshot.json
python -m scripts.signal_engine snapshot.json --config config/defaults.json
```

CLI 向 stdout 输出 JSON。文件/配置解析错误返回退出码 2；不可分析的市场快照输出 WAIT 和原因。程序调用：`from scripts.signal_engine import analyze`，`analyze(snapshot)` 返回同一结构。不提供交易执行功能。

## 文件与使用

- `SKILL.md`：可复用 Skill 入口；将整个文件夹作为 `btc-eth-trading-monitor` 安装到支持 Skill 的客户端，沿用初始骨架名称。
- `references/technical-structure.md`：动态价位与突破确认。
- `references/macro-regime.md`：九种状态、证据优先级与宏观覆盖。
- `references/japan-carry.md`：日债曲线、美日利差、日元及套息传染。
- `references/liquidity.md`：OI/Funding/爆仓、ETF/稳定币、期权、CME。
- `references/risk-management.md`：位置、失效位、扣费盈亏比和输出边界。
- `references/data-contract.md`：输入格式、单位、周期、时效与来源。
- `scripts/indicators.py`、`macro_engine.py`、`signal_engine.py`：纯本地计算。
- `config/defaults.json`：所有门槛、指标定义、状态规则和禁用的历史价位示例。
- `evals/evals.json`、`evals/fixtures/`：可复现实例与期望行为。
- `tests/test_engines.py`：状态覆盖、输入异常和交易位置不变量。

## 第一版范围与限制

本版消费统一快照，不自动抓取实时行情，不提供供应商适配器。配置定义每个指标的单位、观察窗口和最大时效；ETF、CME、债券市场非 24/7，最新已发布数据可在时效范围内使用，但不是盘中实时资金流。事件 flag 是人工/上游基于来源审核的结构化判断，不是自动新闻分类器。

Regime 是可解释、可调的启发式组合，输出所有命中证据与并存状态；无概率校准、无收益验证，也未将合成测试称为实盘回测。每个快照重新计算，不实现隐藏持仓或持久状态；可传入 `previous_regime` 比较切换，但临界值附近可能抖动。

波动率、流动性和宏观缺失会使策略偏保守。跨周期数据应来自同一市场/币对并由上游完成聚合校验；引擎验证各序列的 OHLC、顺序、周期、收盘与时效，但不重建交易所完整行情。期权 gamma、M2 等部分指标仅作披露背景，不直接投票方向，具体见参考文档。

文档中的阈值与信号策略是本项目设计；官方数据参考来源列在宏观、日本与流动性文档中，不代表这些机构认可本策略。

本版替换了早期骨架的 `MacroInputs/classify`、`Structure/state/combined` 布尔接口，统一使用有时间、单位与来源的 `analyze(snapshot)`；旧调用方需要迁移到数据契约格式。旧提交历史保留。
