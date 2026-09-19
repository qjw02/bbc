"""Explainable heuristic regimes, not calibrated probabilities or causal claims."""
from .indicators import number, timestamp


def observations(snapshot, cfg):
    now = timestamp(snapshot["as_of"])
    values, rejected = {}, {}
    supplied = snapshot.get("metrics", {})
    for name, spec in cfg["metrics"].items():
        item = supplied.get(name)
        if item is None:
            rejected[name] = "missing"
            continue
        try:
            value = number(item["value"])
            observed = timestamp(item["observed_at"])
            available = timestamp(item["available_at"])
            age = (now - observed).total_seconds() / 3600
            if available > now or observed > available or age < 0:
                raise ValueError("not available as of analysis time")
            if age > spec["max_age_hours"]:
                raise ValueError("stale")
            if item["unit"] != spec["unit"] or item["horizon"] != spec["horizon"]:
                raise ValueError("unit or horizon mismatch")
            if spec["unit"] == "flag" and value not in (0, 1):
                raise ValueError("flag must be 0 or 1")
            if not isinstance(item.get("source"), str) or not item["source"].strip():
                raise ValueError("source required")
            if "min" in spec and value < spec["min"] or "max" in spec and value > spec["max"]:
                raise ValueError("out of domain")
            values[name] = value
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            rejected[name] = str(exc)
    return values, rejected


def match(rule, values):
    key, operator, threshold = rule
    if key not in values:
        return False
    return values[key] >= threshold if operator == ">=" else values[key] <= threshold


def japan_carry(values, cfg):
    rules = cfg["carry"]
    yen = any(match(r, values) for r in rules["yen"])
    funding = [r[0] for r in rules["funding"] if match(r, values)]
    contagion = [r[0] for r in rules["contagion"] if match(r, values)]
    active = yen and len(funding) >= rules["min_funding"] and len(contagion) >= rules["min_contagion"]
    spreads = {}
    for tenor in ("2y", "10y"):
        us, jp = f"ust{tenor}_pct", f"jgb{tenor}_pct"
        if us in values and jp in values:
            spreads[f"ust_jgb_{tenor}_bp"] = (values[us] - values[jp]) * 100
    curves = {}
    for short, long in (("2y", "10y"), ("10y", "30y"), ("30y", "40y")):
        if f"jgb{short}_pct" in values and f"jgb{long}_pct" in values:
            curves[f"jgb_{short}_{long}_bp"] = (values[f"jgb{long}_pct"] - values[f"jgb{short}_pct"]) * 100
    return {"active": active, "yen_appreciation": yen, "funding_evidence": funding,
            "contagion_evidence": contagion, "spreads": spreads, "curves": curves,
            "intervention_alert": values.get("mof_intervention", 0) > 0 or values.get("mof_rate_check", 0) > 0}


def evaluate_macro(snapshot, cfg):
    values, rejected = observations(snapshot, cfg)
    carry = japan_carry(values, cfg)
    candidates, evidence = [], {}
    for name, spec in cfg["regimes"].items():
        hits = [r[0] for r in spec["rules"] if match(r, values)]
        eligible = len(hits) >= spec["minimum_hits"] and all(match(r, values) for r in spec.get("required", []))
        evidence[name] = {"hits": hits, "eligible": eligible}
        if eligible:
            candidates.append(name)
    if carry["active"]:
        candidates.append("Carry Trade Unwind")
    selected = next((r for r in cfg["regime_priority"] if r in candidates), "Neutral/Range")
    previous = snapshot.get("previous_regime")
    if previous is not None and previous not in cfg["regime_priority"] + ["Neutral/Range"]:
        raise ValueError("unknown previous_regime")
    required = cfg["required_metrics"]
    missing = [key for key in required if key not in values]
    return {"regime": selected, "previous_regime": previous,
            "changed": previous is not None and previous != selected,
            "active_regimes": candidates, "evidence": evidence, "japan": carry,
            "coverage": len(values) / len(cfg["metrics"]), "missing_required": missing,
            "rejected_metrics": rejected, "values": values,
            "risk_off": selected in cfg["risk_off_regimes"]}
