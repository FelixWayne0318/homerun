import asyncio

from services.trader_orchestrator.exit_executor import submit_child_order


class _FailedSubmit:
    status = "failed"
    error_message = "no orders found to match"
    payload: dict = {}
    order_id = None


async def _place_failing(**kwargs):
    return _FailedSubmit()


def _child():
    return {"level_idx": 0, "price": 0.50, "size": 10.0, "status": "planned"}


def test_unfilled_fak_exit_is_requeued_with_one_tick_step():
    child = _child()
    asyncio.run(
        submit_child_order(
            child=child,
            token_id="token",
            side="SELL",
            min_order_size_usd=1.0,
            place_order=_place_failing,
        )
    )
    assert child["status"] == "planned"
    assert child["price"] == 0.49
    assert child["submit_attempts"] == 1


def test_unfilled_fak_exit_stops_after_bounded_attempts():
    child = _child()
    for _ in range(3):
        asyncio.run(
            submit_child_order(
                child=child,
                token_id="token",
                side="SELL",
                min_order_size_usd=1.0,
                place_order=_place_failing,
            )
        )
    assert child["status"] == "failed"
    assert child["submit_attempts"] == 3
    assert child["price"] == 0.48
