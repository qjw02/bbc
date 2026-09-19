"""Run: python -m scripts.signal_engine snapshot.json [--config path]."""
import argparse
import json
from pathlib import Path

from .indicators import closed_candles, number, structure, swing_levels, timestamp, trend
from .macro_engine import evaluate_macro

ROOT = Path(__file__).resolve().parents[1]
SIGNALS = {"LONG BIAS", "SHORT BIAS", "WAIT", "STRUCTURE CHANGE"}


def load_config(path=None):
    cfg = json.loads(Path(path or ROOT / "config/defaults.json").read_text(encoding="utf-8"))
    for key in ("breakout_buffer_atr", "retest_tolerance_atr", "entry_half_width_atr",
                "stop_buffer_atr", "max_distance_atr", "min_volume_ratio", "min_rr", "tp2_r"):
        if number(cfg["technical"][key]) <= 0:
            raise ValueError(f"config: {key} must be positive")
    if cfg["technical"]["tp2_r"] <= cfg["technical"]["min_rr"]:
        raise ValueError("tp2_r must exceed min_rr")
    for key in ("lookback", "atr_period", "minimum_candles"):
        value = cfg["technical"][key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError(f"config: invalid {key}")
    if cfg["technical"]["minimum_candles"] < max(cfg["technical"]["lookback"] + 2, 24):
        raise ValueError("minimum_candles must cover lookback plus confirmation")
    if cfg["technical"]["minimum_candles"] < cfg["technical"]["atr_period"] + 3:
        raise ValueError("minimum_candles must cover ATR history")
    if cfg["technical"]["stop_buffer_atr"] <= cfg["technical"]["entry_half_width_atr"]:
        raise ValueError("stop must lie outside entry zone")
    if not 0 < number(cfg["minimum_coverage"]) <= 1:
        raise ValueError("coverage must be within (0, 1]")
    if not 0 <= number(cfg["roundtrip_cost_bps"]) < 10000:
        raise ValueError("invalid roundtrip cost")
    if number(cfg["quote_max_age_seconds"]) <= 0:
        raise ValueError("quote maximum age must be positive")
    for spec in cfg["metrics"].values():
        if number(spec["max_age_hours"]) <= 0:
            raise ValueError("metric maximum age must be positive")
    if any(key not in cfg["metrics"] for key in cfg["required_metrics"]):
        raise ValueError("unknown required metric")
    for name, value in cfg["derivatives"].items():
        if number(value) <= 0:
            raise ValueError(f"invalid derivative threshold: {name}")
    rule_groups = list(cfg["regimes"].values())
    for group in rule_groups:
        if not 1 <= group["minimum_hits"] <= len(group["rules"]):
            raise ValueError("invalid regime minimum_hits")
    rules = [r for group in rule_groups for r in group["rules"] + group.get("required", [])]
    rules += [r for name in ("yen", "funding", "contagion") for r in cfg["carry"][name]]
    for key, operator, threshold in rules:
        if key not in cfg["metrics"] or operator not in (">=", "<="):
            raise ValueError("invalid regime rule")
        number(threshold)
    expected = set(cfg["regimes"]) | {"Carry Trade Unwind"}
    if set(cfg["regime_priority"]) != expected or len(cfg["regime_priority"]) != len(expected):
        raise ValueError("regime priority must contain each state exactly once")
    for key, group in (("min_funding", "funding"), ("min_contagion", "contagion")):
        if not 1 <= cfg["carry"][key] <= len(cfg["carry"][group]):
            raise ValueError("invalid carry evidence minimum")
    return cfg


def analyze(snapshot, cfg=None):
    cfg = cfg or load_config()
    if not isinstance(snapshot, dict):
        return {"signal": "WAIT", "plan": None, "reasons": ["Invalid input: expected JSON object"],
                "read_only": True, "symbol": None, "as_of": None}
    result = {"signal": "WAIT", "plan": None, "reasons": [], "read_only": True,
              "symbol": snapshot.get("symbol"), "as_of": snapshot.get("as_of")}
    try:
        if snapshot.get("symbol") not in ("BTC", "ETH"):
            raise ValueError("symbol must be BTC or ETH")
        t = cfg["technical"]
        candles = {tf: closed_candles(snapshot["candles"][tf], tf, snapshot["as_of"],
                                      t["minimum_candles"]) for tf in ("15m", "1H", "4H")}
        quote = snapshot["quote"]
        price = number(quote["price"])
        age = (timestamp(snapshot["as_of"]) - timestamp(quote["as_of"])).total_seconds()
        if price <= 0 or not 0 <= age <= cfg["quote_max_age_seconds"] or not quote.get("source"):
            raise ValueError("invalid, future or stale quote")
        s = structure(candles["1H"], t)
        macro = evaluate_macro(snapshot, cfg)
        result.update(structure=s, trends={tf: trend(rows) for tf, rows in candles.items()}, macro=macro)
        reasons = result["reasons"]
        values = macro["values"]
        if macro["missing_required"]:
            reasons.append("Required observations missing/stale: " + ", ".join(macro["missing_required"]))
            return result
        if macro["coverage"] < cfg["minimum_coverage"]:
            reasons.append("Insufficient cross-market coverage")
            return result
        risk = []
        if macro["risk_off"]:
            risk.append(macro["regime"])
        if macro["rejected_metrics"]:
            risk.append("Partial coverage: " + ", ".join(macro["rejected_metrics"]))
        if macro["japan"]["intervention_alert"]:
            risk.append("MOF intervention/rate-check reversal risk")
        if values.get("options_atm_iv_pct", 0) >= cfg["derivatives"]["iv_warning"]:
            risk.append("Elevated options implied volatility")
        if values.get("options_term_slope_pp", 0) < 0:
            risk.append("Inverted options volatility term structure")
        if values.get("options_expiry_hours", 999) < 24:
            risk.append("Near options expiry; gamma effects are conditional")
        if values.get("event_risk", 0) >= 1:
            reasons.append("High-impact event blackout")
            return result
        last, prior = candles["1H"][-1], candles["1H"][-2]
        move = (last["close"] / prior["close"] - 1) * 100
        if abs(move) > cfg["derivatives"]["waterfall_pct"] or "Crypto-native Leverage Flush" in macro["active_regimes"]:
            reasons.append("Disorderly leverage flush/extended move: wait for a new base")
            return result
        if s["false_breakout"] or s["liquidity_sweep"]:
            reasons.append("False breakout/liquidity sweep: require a fresh confirmed structure")
            return result
        direction = s["direction"]
        if not direction:
            reasons.append("No 1H close plus continuation/retest confirmation")
            return result
        expected = "up" if direction == "long" else "down"
        if result["trends"]["4H"] != expected:
            result["signal"] = "STRUCTURE CHANGE"
            reasons.append("Confirmed 1H break conflicts with 4H trend; wait for realignment")
            return result
        if result["trends"]["15m"] != expected:
            reasons.append("15m timing is not aligned")
            return result
        if direction == "long" and macro["risk_off"]:
            reasons.append("Macro risk-off but price holds/breaks higher: refusal to fall; do not mechanically short")
            return result
        d = cfg["derivatives"]
        funding = values.get("funding_pct_8h", 0)
        crowded = values.get("oi_change_pct_1h", 0) >= d["crowded_oi_pct"] and (
            funding >= d["crowded_funding_pct"] if direction == "long" else funding <= -d["crowded_funding_pct"])
        if crowded:
            reasons.append("Crowded leverage/funding; wait for reset")
            return result
        # Slow flows and derivatives constrain confidence, never create direction.
        headwinds = []
        sign = 1 if direction == "long" else -1
        for key in ("etf_flow_usd_m", "stablecoin_change_pct_7d", "cme_basis_annual_pct"):
            if key in values and values[key] * sign < 0:
                headwinds.append(key)
        if values.get("options_skew_put_minus_call_pp", 0) * sign > d["skew_warning_pp"]:
            headwinds.append("options downside/upside protection demand")
        if values.get("cme_oi_change_pct_1d", 0) < -d["cme_oi_warning_pct"]:
            headwinds.append("CME position reduction")
        risk.extend(headwinds)
        if len(headwinds) >= d["max_flow_headwinds"]:
            reasons.append("Multiple flow/derivative headwinds")
            return result
        level = s["resistance"] if direction == "long" else s["support"]
        volatility = s["atr"]
        if abs(price - level) > t["max_distance_atr"] * volatility or sign * (price - level) < 0:
            reasons.append("Unattractive location or lost level: do not chase")
            return result
        if s["breakout_volume_ratio"] < t["min_volume_ratio"]:
            reasons.append("Breakout volume is insufficient")
            return result
        half = t["entry_half_width_atr"] * volatility
        zone = [level - half, level + half]
        stop = level - sign * t["stop_buffer_atr"] * volatility
        worst_entry = zone[1] if sign == 1 else zone[0]
        risk_distance = abs(worst_entry - stop)
        costs = worst_entry * (cfg["roundtrip_cost_bps"] / 10000)
        levels = sorted(set(s["levels"] + swing_levels(candles["4H"])), reverse=sign < 0)
        obstacles = [x for x in levels if sign * (x - worst_entry) > 0]
        tp1 = obstacles[0] if obstacles else worst_entry + sign * (t["min_rr"] * (risk_distance + costs) + costs)
        rr = (sign * (tp1 - worst_entry) - costs) / (risk_distance + costs)
        if rr + 1e-9 < t["min_rr"]:
            reasons.append("Nearest opposing structure leaves insufficient net reward/risk")
            return result
        later = [x for x in obstacles if sign * (x - tp1) > 0]
        tp2 = later[0] if later else worst_entry + sign * max(t["tp2_r"] * (risk_distance + costs) + costs,
                                                              abs(tp1 - worst_entry) + risk_distance)
        if min(*zone, stop, tp1, tp2) <= 0:
            reasons.append("Invalid price geometry")
            return result
        result["signal"] = "LONG BIAS" if direction == "long" else "SHORT BIAS"
        result["plan"] = {"entry_zone": zone,
            "trigger": f"Conditional {direction}: quote returns to entry zone; a new closed 15m candle holds {'above' if sign == 1 else 'below'} {level:g}; cancel if 1H loses level or regime/data changes",
            "invalidation": stop, "tp1": tp1, "tp2": tp2, "net_rr_tp1": rr,
            "target_basis": {"tp1": "historical swing" if obstacles else "R projection, not observed liquidity",
                             "tp2": "historical swing" if later else "R projection, not observed liquidity"},
            "expires_at_next_1h_close": True,
            "main_risk": "; ".join(risk) if risk else "Breakout failure and execution slippage"}
        reasons.append("Confirmed structure, aligned trend, attractive pullback/rebound location")
        return result
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        result["reasons"].append(f"Invalid input: {exc}")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot")
    parser.add_argument("--config")
    args = parser.parse_args()
    try:
        cfg = load_config(args.config)
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        result = analyze(snapshot, cfg)
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        parser.exit(2, f"Input/config error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
