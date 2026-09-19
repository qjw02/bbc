from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Structure:
    price: float
    bullish_level: float
    bearish_level: float
    one_hour_close: float
    retest_ok: bool=False
    follow_through: bool=False

def state(x: Structure) -> str:
    bull = x.one_hour_close > x.bullish_level and (x.retest_ok or x.follow_through)
    bear = x.one_hour_close < x.bearish_level and (x.retest_ok or x.follow_through)
    if bull:
        return "BULLISH"
    if bear:
        return "BEARISH"
    return "WAIT"

def combined(btc: Structure, eth: Structure, macro_regime: str) -> str:
    b, e = state(btc), state(eth)
    risk_off = macro_regime in {"CARRY_TRADE_UNWIND","CREDIT_STRESS","WAR_OIL_SHOCK","FED_TIGHTENING_SHOCK"}
    if b == "BULLISH" and e == "BULLISH" and not risk_off:
        return "LONG BIAS"
    if b == "BEARISH" and e == "BEARISH":
        return "SHORT BIAS"
    return "WAIT"
