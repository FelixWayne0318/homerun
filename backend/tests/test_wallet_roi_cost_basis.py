import pytest

from services.wallet_discovery import WalletDiscoveryEngine
from utils.wallet_metrics import (
    COST_QUALITY_ESTIMATED,
    COST_QUALITY_EXACT,
    COST_QUALITY_UNKNOWN,
    resolve_closed_position_cost,
)


@pytest.mark.parametrize(
    ("position", "expected_cost", "expected_quality"),
    [
        ({"initialValue": 120.5}, 120.5, COST_QUALITY_EXACT),
        ({"entry_cost_usdc": 80.0}, 80.0, COST_QUALITY_EXACT),
        (
            {"realizedPnl": 31211.1648, "percent_realized_pnl": 4800},
            650.2326,
            COST_QUALITY_ESTIMATED,
        ),
        ({"avgPrice": 0.5, "size": 40}, 20.0, COST_QUALITY_ESTIMATED),
        ({"realizedPnl": 100}, None, COST_QUALITY_UNKNOWN),
    ],
)
def test_resolve_closed_position_cost(position, expected_cost, expected_quality):
    cost, quality = resolve_closed_position_cost(position)
    assert quality == expected_quality
    if expected_cost is None:
        assert cost is None
    else:
        assert cost == pytest.approx(expected_cost)


def test_accuracy_first_stats_use_total_pnl_over_invested():
    engine = WalletDiscoveryEngine()
    closed_positions = [
        {
            "market": "m1",
            "realizedPnl": 31211.1648,
            "initialValue": 0,
            "percent_realized_pnl": 4800,
        }
    ]
    snapshot = {
        "total_trades": 1,
        "open_positions": 0,
        "total_invested": 650.2326,
        "total_returned": 31861.3974,
        "realized_pnl": 31211.1648,
        "unrealized_pnl": 0.0,
        "total_pnl": 31211.1648,
        "roi_quality": COST_QUALITY_ESTIMATED,
        "cost_coverage": 1.0,
    }

    stats = engine._build_accuracy_first_stats(
        base_stats=engine._empty_stats(),
        pnl_snapshot=snapshot,
        closed_positions=closed_positions,
    )

    assert stats["avg_roi"] == pytest.approx(4800.0)
    assert stats["roi_quality"] == COST_QUALITY_ESTIMATED
    assert stats["cost_coverage"] == pytest.approx(1.0)


def test_accuracy_first_stats_return_none_when_cost_is_unknown():
    engine = WalletDiscoveryEngine()
    closed_positions = [{"market": "m1", "realizedPnl": 100.0}]
    snapshot = {
        "total_trades": 1,
        "open_positions": 0,
        "total_invested": 0.0,
        "total_returned": 0.0,
        "realized_pnl": 100.0,
        "unrealized_pnl": 0.0,
        "total_pnl": 100.0,
        "roi_quality": COST_QUALITY_UNKNOWN,
        "cost_coverage": 0.0,
    }

    stats = engine._build_accuracy_first_stats(
        base_stats=engine._empty_stats(),
        pnl_snapshot=snapshot,
        closed_positions=closed_positions,
    )

    assert stats["avg_roi"] is None
    assert stats["roi_quality"] == COST_QUALITY_UNKNOWN


def test_trade_stats_roi_is_capital_weighted():
    engine = WalletDiscoveryEngine()
    trades = [
        {"market": "m1", "side": "BUY", "size": 100, "price": 1.0},
        {"market": "m1", "side": "SELL", "size": 100, "price": 2.0},
        {"market": "m2", "side": "BUY", "size": 1000, "price": 1.0},
        {"market": "m2", "side": "SELL", "size": 1000, "price": 1.01},
    ]

    stats = engine._calculate_trade_stats(trades)

    assert stats["total_invested"] == pytest.approx(1100.0)
    assert stats["total_pnl"] == pytest.approx(110.0)
    assert stats["avg_roi"] == pytest.approx(10.0)
