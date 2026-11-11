from __future__ import annotations

from typing import Any, Iterable

COST_QUALITY_EXACT = "exact"
COST_QUALITY_ESTIMATED = "estimated"
COST_QUALITY_UNKNOWN = "unknown"

_COST_FIELDS = (
    "initialValue",
    "initial_value",
    "entry_cost_usdc",
    "entryCostUsdc",
    "total_cost_usdc",
    "totalCostUsdc",
)

_PNL_FIELDS = ("realizedPnl", "realized_pnl", "realizedPnlUsdc")
_PERCENT_FIELDS = ("percent_realized_pnl", "percentRealizedPnl", "percent_pnl")
_AVG_PRICE_FIELDS = ("avgPrice", "avg_price")
_SIZE_FIELDS = ("size", "current_size", "currentSize")


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _first_positive(position: dict, fields: Iterable[str]) -> float:
    for field in fields:
        value = _to_float(position.get(field))
        if value > 0:
            return value
    return 0.0


def resolve_closed_position_cost(position: dict) -> tuple[float | None, str]:
    """Resolve the cost basis of one closed position and label its quality.

    The upstream closed-positions feed sometimes reports initialValue=0 for
    redeemed positions while still exposing percent_realized_pnl. In that case
    the cost is reconstructed from realized PnL and the reported percentage;
    it is usable for display but must not be treated as an exact cash cost.
    """
    if not isinstance(position, dict):
        return None, COST_QUALITY_UNKNOWN

    exact_cost = _first_positive(position, _COST_FIELDS)
    if exact_cost > 0:
        return exact_cost, COST_QUALITY_EXACT

    realized_pnl = _first_positive(position, _PNL_FIELDS)
    percent = _to_float(position.get(_PERCENT_FIELDS[0]))
    if percent == 0:
        percent = _to_float(position.get(_PERCENT_FIELDS[1]))
    if percent == 0:
        percent = _to_float(position.get(_PERCENT_FIELDS[2]))

    if realized_pnl > 0 and abs(percent) > 1e-9:
        implied_cost = abs(realized_pnl / (percent / 100.0))
        if implied_cost > 0:
            return implied_cost, COST_QUALITY_ESTIMATED

    avg_price = _first_positive(position, _AVG_PRICE_FIELDS)
    size = _first_positive(position, _SIZE_FIELDS)
    if avg_price > 0 and size > 0:
        return avg_price * size, COST_QUALITY_ESTIMATED

    return None, COST_QUALITY_UNKNOWN


def combine_cost_quality(qualities: Iterable[str], unknown_positions: int = 0) -> str:
    if unknown_positions > 0:
        return COST_QUALITY_UNKNOWN
    values = list(qualities)
    if not values:
        return COST_QUALITY_UNKNOWN
    if any(value == COST_QUALITY_UNKNOWN for value in values):
        return COST_QUALITY_UNKNOWN
    if any(value == COST_QUALITY_ESTIMATED for value in values):
        return COST_QUALITY_ESTIMATED
    return COST_QUALITY_EXACT


def summarize_position_costs(positions: Iterable[dict]) -> dict:
    """Aggregate cost basis, realized PnL, quality counts and coverage."""
    total_cost = 0.0
    realized_pnl = 0.0
    total_positions = 0
    known_positions = 0
    exact_positions = 0
    estimated_positions = 0
    unknown_positions = 0
    qualities: list[str] = []

    for position in positions:
        if not isinstance(position, dict):
            continue
        total_positions += 1
        pnl = _to_float(position.get("realizedPnl"))
        if pnl == 0:
            pnl = _to_float(position.get("realized_pnl"))
        realized_pnl += pnl

        cost, quality = resolve_closed_position_cost(position)
        qualities.append(quality)
        if cost is None:
            unknown_positions += 1
            continue

        known_positions += 1
        total_cost += cost
        if quality == COST_QUALITY_EXACT:
            exact_positions += 1
        else:
            estimated_positions += 1

    coverage = known_positions / total_positions if total_positions > 0 else 0.0
    return {
        "total_cost": total_cost,
        "realized_pnl": realized_pnl,
        "total_positions": total_positions,
        "known_positions": known_positions,
        "exact_positions": exact_positions,
        "estimated_positions": estimated_positions,
        "unknown_positions": unknown_positions,
        "cost_coverage": coverage,
        "cost_quality": combine_cost_quality(qualities, unknown_positions),
    }
