"""Causal OHLCV indicators; timestamps are UTC candle CLOSE times."""
from datetime import datetime, timezone
from math import isfinite
from statistics import mean


def timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return dt.astimezone(timezone.utc)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("expected finite numeric value")
    return float(value)


def closed_candles(rows, timeframe, as_of, minimum=30):
    seconds = {"15m": 900, "1H": 3600, "4H": 14400}[timeframe]
    now = timestamp(as_of)
    result, previous = [], None
    for row in rows:
        end = timestamp(row["close_time"])
        if previous is not None and (end - previous).total_seconds() != seconds:
            raise ValueError(f"{timeframe}: unordered, duplicate or missing candles")
        if end.timestamp() % seconds:
            raise ValueError(f"{timeframe}: candle is not UTC interval aligned")
        previous = end
        if end > now or row.get("closed") is not True:
            continue
        o, h, l, c, v = (number(row[k]) for k in ("open", "high", "low", "close", "volume"))
        if min(o, h, l, c) <= 0 or v < 0 or not l <= min(o, c) <= max(o, c) <= h:
            raise ValueError(f"{timeframe}: invalid OHLCV")
        result.append(row)
    if len(result) < minimum:
        raise ValueError(f"{timeframe}: need at least {minimum} closed candles")
    if any((timestamp(b["close_time"]) - timestamp(a["close_time"])).total_seconds() != seconds
           for a, b in zip(result, result[1:])):
        raise ValueError(f"{timeframe}: gap in closed candles")
    if (now - timestamp(result[-1]["close_time"])).total_seconds() > seconds * 1.5:
        raise ValueError(f"{timeframe}: stale candles")
    return result


def ema(values, period):
    value = values[0]
    alpha = 2 / (period + 1)
    for item in values[1:]:
        value += alpha * (item - value)
    return value


def atr(rows, period=14):
    ranges = [max(r["high"] - r["low"], abs(r["high"] - p["close"]),
                  abs(r["low"] - p["close"])) for p, r in zip(rows, rows[1:])]
    return mean(ranges[-period:])


def trend(rows):
    closes = [r["close"] for r in rows]
    fast, slow = ema(closes, 8), ema(closes, 21)
    slope = fast - ema(closes[:-3], 8)
    threshold = atr(rows) * 0.1
    if fast - slow > threshold and slope > 0:
        return "up"
    if slow - fast > threshold and slope < 0:
        return "down"
    return "range"


def swing_levels(rows, width=2):
    # A pivot exists only once its right-hand candles have closed.
    levels = []
    for i in range(width, len(rows) - width):
        window = rows[i-width:i+width+1]
        if rows[i]["high"] == max(r["high"] for r in window):
            levels.append(rows[i]["high"])
        if rows[i]["low"] == min(r["low"] for r in window):
            levels.append(rows[i]["low"])
    return sorted(set(levels))


def structure(rows, cfg):
    # Freeze the tested range BEFORE both breakout/confirmation candles.
    history, first, last = rows[:-2], rows[-2], rows[-1]
    window = history[-cfg["lookback"]:]
    support = min(r["low"] for r in window)
    resistance = max(r["high"] for r in window)
    volatility = atr(history, cfg["atr_period"])
    if volatility <= 0:
        raise ValueError("zero ATR: no actionable structure")
    buffer = volatility * cfg["breakout_buffer_atr"]
    tolerance = volatility * cfg["retest_tolerance_atr"]
    up = first["close"] > resistance + buffer
    down = first["close"] < support - buffer
    up_hold = last["close"] > resistance + buffer
    down_hold = last["close"] < support - buffer
    up_retest = resistance - tolerance <= last["low"] <= resistance + tolerance
    down_retest = support - tolerance <= last["high"] <= support + tolerance
    direction = None
    confirmation = None
    if up and up_hold and (up_retest or last["close"] > first["close"]):
        direction, confirmation = "long", "retest" if up_retest else "continuation"
    elif down and down_hold and (down_retest or last["close"] < first["close"]):
        direction, confirmation = "short", "retest" if down_retest else "continuation"
    fake = (up and last["close"] <= resistance) or (down and last["close"] >= support)
    sweep = any((r["high"] > resistance + buffer and r["close"] <= resistance) or
                (r["low"] < support - buffer and r["close"] >= support) for r in (first, last))
    baseline_volume = mean(r["volume"] for r in window)
    return {"support": support, "resistance": resistance, "atr": volatility,
            "direction": direction, "confirmation": confirmation,
            "false_breakout": fake, "liquidity_sweep": sweep,
            "breakout_volume_ratio": first["volume"] / baseline_volume if baseline_volume else 0,
            "trend": trend(rows), "levels": swing_levels(history)}
