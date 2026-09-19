---
name: btc-eth-trading-monitor
description: Analyze BTC/USDT and ETH/USDT using market structure, derivatives, capital flows and macro regimes. Use for breakout/breakdown confirmation, liquidity sweeps, long/short setup selection, macro risk and carry-trade risk. Read-only; never place trades.
---

# BTC/ETH Trading Monitor

## Objective
Return exactly one market state: LONG BIAS, SHORT BIAS, WAIT, or STRUCTURE CHANGE.

Prefer no trade over a poor entry. In an uptrend wait for a pullback; in a downtrend wait for a rebound. Never chase an extended candle.

## Freshness
Always obtain fresh market and macro data before making a current-market judgment. Label stale/missing inputs. Do not silently substitute old values.

## Analysis order
1. Read 15m/1h/4h BTC and ETH structure.
2. Load current configurable structural levels; never permanently hard-code historical levels.
3. Test breakout/breakdown quality: 1h close, follow-through, retest, volume.
4. Detect liquidity sweeps and failed breakouts.
5. Read derivatives: OI, funding, basis, liquidations, options.
6. Read crypto capital flows: ETF, stablecoins, Coinbase premium, CME.
7. Determine macro regime using references/macro-regime.md.
8. Check Japan carry risk using references/japan-carry.md.
9. Apply risk rules.
10. Produce one preferred setup only when location is attractive.

## Effective breakout
A wick beyond a level is not confirmation. Prefer a 1h close beyond it plus follow-through or a successful retest. Volume and healthy OI improve confidence. A vertical move driven mainly by liquidations is a squeeze until proven otherwise.

## News-price divergence
Bearish news + refusal to fall = bullish resilience.
Bullish news + refusal to rise = bearish weakness.
After CPI, FOMC, BOJ or geopolitical shocks, avoid judging only the first algorithmic move; prefer 15m-1h confirmation.

## Output
Market state:
BTC structure:
ETH structure:
Macro regime:
Derivatives/capital flow:
Preferred action: LONG / SHORT / WAIT
Preferred entry: ONE zone
Trigger:
Invalidation:
TP1:
TP2:
Main risk:

If monitoring mode finds no meaningful structural change, output only that there is no meaningful change.

Read references/technical-structure.md, references/liquidity.md, references/macro-regime.md, references/japan-carry.md and references/risk-management.md when relevant.
