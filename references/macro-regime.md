# Macro Regime Engine

Classify:
1. LIQUIDITY_RISK_ON
2. NORMAL_RISK_ON
3. NEUTRAL_RANGE
4. INFLATION_SHOCK
5. FED_TIGHTENING_SHOCK
6. CARRY_TRADE_UNWIND
7. CREDIT_STRESS
8. WAR_OIL_SHOCK
9. CRYPTO_LEVERAGE_FLUSH

Inputs: Fed/Fed funds/SOFR, UST 2Y/10Y/30Y, 10Y TIPS real yield, DXY, S&P 500/Nasdaq, VIX, MOVE, HY/IG spreads, gold, Brent/WTI, CPI/PCE/NFP/PMI, Fed balance sheet, TGA, RRP, bank reserves, M2, ETF/stablecoin/CME flows.

Weights are dynamic. During an oil shock, oil/inflation/yields/Fed get higher weight. During credit stress, spreads/VIX/MOVE dominate. Slow liquidity variables set background regime rather than intraday entries.

Do not double-count causal chains (e.g. oil -> inflation -> yields -> Fed) as four independent signals.
