from __future__ import annotations

def pct_change(new: float, old: float) -> float:
    if old == 0:
        raise ValueError("old must be non-zero")
    return (new / old - 1.0) * 100.0

def spread(a: float, b: float) -> float:
    return a - b

def accepted_break(close: float, level: float, direction: str, retest_ok: bool=False, follow_through: bool=False) -> bool:
    beyond = close > level if direction == "up" else close < level
    return beyond and (retest_ok or follow_through)
