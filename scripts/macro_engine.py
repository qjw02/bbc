from __future__ import annotations
from dataclasses import dataclass

@dataclass
class MacroInputs:
    yields_up: bool=False
    real_yields_up: bool=False
    dxy_up: bool=False
    vix_up: bool=False
    move_up: bool=False
    credit_spreads_wider: bool=False
    oil_shock: bool=False
    war_escalation: bool=False
    jpy_appreciating_fast: bool=False
    us_jp_spread_compressing_fast: bool=False
    equities_down: bool=False
    crypto_oi_falling: bool=False
    liquidity_expanding: bool=False

def classify(x: MacroInputs) -> str:
    if x.jpy_appreciating_fast and x.us_jp_spread_compressing_fast and x.equities_down:
        return "CARRY_TRADE_UNWIND"
    if x.credit_spreads_wider and x.vix_up and x.move_up:
        return "CREDIT_STRESS"
    if x.oil_shock and x.war_escalation:
        return "WAR_OIL_SHOCK"
    if x.yields_up and x.real_yields_up and x.dxy_up:
        return "FED_TIGHTENING_SHOCK"
    if x.oil_shock and x.yields_up:
        return "INFLATION_SHOCK"
    if x.crypto_oi_falling and not x.equities_down:
        return "CRYPTO_LEVERAGE_FLUSH"
    if x.liquidity_expanding and not x.dxy_up and not x.real_yields_up:
        return "LIQUIDITY_RISK_ON"
    return "NEUTRAL_RANGE"
