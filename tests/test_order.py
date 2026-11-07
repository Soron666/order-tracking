"""Tests for the order / watcher contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from order_tracking import Order, OrderStatus, SmsNotifier, Watcher
from order_tracking.watchers.kitchen import KitchenScreen


class RecordingWatcher(Watcher):
    """A watcher that only records what it was told."""

    def __init__(self) -> None:
        self.seen: list[OrderStatus] = []

    def update(self, order: Order) -> None:
        self.seen.append(order.status)


# ----------------------------------------------------------------------
# status
# ----------------------------------------------------------------------
def test_new_order_is_placed() -> None:
    order = Order()
    assert order.status is OrderStatus.PLACED
    assert order.order_id == "ORD-1001"


def test_change_status_updates_the_order() -> None:
    order = Order()
    order.change_status(OrderStatus.COOKING)
    assert order.status is OrderStatus.COOKING


# ----------------------------------------------------------------------
# rule 4: one change tells every watcher on the list at that moment
# ----------------------------------------------------------------------
def test_every_watcher_is_told_once_per_change() -> None:
    order = Order()
    first, second = RecordingWatcher(), RecordingWatcher()
    order.add_watcher(first)
    order.add_watcher(second)

    order.change_status(OrderStatus.COOKING)

    assert first.seen == [OrderStatus.COOKING]
    assert second.seen == [OrderStatus.COOKING]


def test_watcher_added_later_only_hears_later_changes() -> None:
    order = Order()
    early = RecordingWatcher()
    order.add_watcher(early)
    order.change_status(OrderStatus.COOKING)

    late = RecordingWatcher()
    order.add_watcher(late)
    order.change_status(OrderStatus.OUT_FOR_DELIVERY)

    assert early.seen == [OrderStatus.COOKING, OrderStatus.OUT_FOR_DELIVERY]
    assert late.seen == [OrderStatus.OUT_FOR_DELIVERY]


def test_watcher_removed_stops_receiving_updates() -> None:
    order = Order()
    watcher = RecordingWatcher()
    order.add_watcher(watcher)
    order.change_status(OrderStatus.COOKING)

    order.remove_watcher(watcher)
    order.change_status(OrderStatus.OUT_FOR_DELIVERY)

    assert watcher.seen == [OrderStatus.COOKING]


def test_adding_the_same_watcher_twice_notifies_it_once() -> None:
    order = Order()
    watcher = RecordingWatcher()
    order.add_watcher(watcher)
    order.add_watcher(watcher)

    order.change_status(OrderStatus.COOKING)

    assert watcher.seen == [OrderStatus.COOKING]
    assert len(order.watchers) == 1


def test_removing_an_unknown_watcher_is_harmless() -> None:
    order = Order()
    watcher = RecordingWatcher()
    order.remove_watcher(watcher)
    order.change_status(OrderStatus.COOKING)
    assert order.watchers == []


# ----------------------------------------------------------------------
# rule 3: watchers can come and go at any time - including mid-notification
# ----------------------------------------------------------------------
def test_a_watcher_may_remove_itself_while_being_notified() -> None:
    order = Order()
    order.change_status(OrderStatus.PLACED)

    class SelfRemoving(Watcher):
        def update(self, order: Order) -> None:
            order.remove_watcher(self)

    quitter = SelfRemoving()
    survivor = RecordingWatcher()
    order.add_watcher(quitter)
    order.add_watcher(survivor)

    order.change_status(OrderStatus.COOKING)

    assert survivor.seen == [OrderStatus.COOKING]
    assert order.watchers == [survivor]


def test_a_watcher_may_add_another_watcher_while_being_notified() -> None:
    order = Order()
    newcomer = RecordingWatcher()

    class Adder(Watcher):
        def update(self, order: Order) -> None:
            order.add_watcher(newcomer)

    order.add_watcher(Adder())
    order.change_status(OrderStatus.COOKING)

    # The newcomer joined mid-notification, so it misses that change.
    assert newcomer.seen == []
    order.change_status(OrderStatus.OUT_FOR_DELIVERY)
    assert newcomer.seen == [OrderStatus.OUT_FOR_DELIVERY]


# ----------------------------------------------------------------------
# rule 2: the order knows nothing about phones or kitchens
# ----------------------------------------------------------------------
def test_order_does_not_mention_phone_or_kitchen() -> None:
    """Rule 2: the order must not know about specific reporting channels."""
    source = (
        Path(__file__).resolve().parent.parent / "order_tracking" / "order.py"
    ).read_text(encoding="utf-8")
    lowered = source.lower()
    for forbidden in ("sms", "kitchen", "phone", "notifier", "screen"):
        assert forbidden not in lowered, f"order.py must not mention {forbidden!r}"


def test_order_accepts_any_object_with_an_update_method() -> None:
    """The order only relies on the Watcher interface - duck typing works."""

    class Duck:
        def __init__(self) -> None:
            self.seen = []

        def update(self, order: Order) -> None:
            self.seen.append(order.status.value)

    order = Order()
    duck = Duck()
    order.add_watcher(duck)  # type: ignore[arg-type]
    order.change_status(OrderStatus.COOKING)

    assert duck.seen == ["Cooking"]


# ----------------------------------------------------------------------
# the required output
# ----------------------------------------------------------------------
EXPECTED_OUTPUT = """\
Order is now: Cooking
SMS to Rahim: your order is now Cooking
Kitchen screen: Cooking
Order is now: Out for delivery
SMS to Rahim: your order is now Out for delivery
Kitchen screen: Out for delivery
Order is now: Delivered
SMS to Rahim: your order is now Delivered
"""


def test_demo_prints_the_required_output(capsys: pytest.CaptureFixture[str]) -> None:
    from order_tracking.demo import main

    main()

    assert capsys.readouterr().out == EXPECTED_OUTPUT


def test_kitchen_is_not_notified_when_the_order_is_delivered(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from order_tracking.demo import main

    main()
    out = capsys.readouterr().out

    assert "Kitchen screen: Delivered" not in out
    assert out.count("Kitchen screen:") == 2


def test_kitchen_removes_itself_once_the_food_leaves() -> None:
    order = Order()
    sms = SmsNotifier(recipient="Rahim", printer=lambda _msg: None)
    kitchen = KitchenScreen(printer=lambda _msg: None)

    order.add_watcher(sms)
    order.add_watcher(kitchen)

    order.change_status(OrderStatus.COOKING)
    assert kitchen in order.watchers

    order.change_status(OrderStatus.OUT_FOR_DELIVERY)
    assert kitchen not in order.watchers
    assert sms in order.watchers
