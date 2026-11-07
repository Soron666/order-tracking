"""The kitchen screen watcher."""

from __future__ import annotations

from typing import Callable

from ..order import Order
from ..status import OrderStatus
from ..watcher import Watcher

Printer = Callable[[str], None]


class KitchenScreen(Watcher):
    """The display in the kitchen.

    The kitchen only cares about an order while the food is still in the
    kitchen.  As soon as the order moves to ``OUT_FOR_DELIVERY`` the food has
    left, so the screen removes itself from the watch list.

    That is why the ``Delivered`` change is never shown on the kitchen
    screen - not because the order special-cases kitchens, but because the
    kitchen is no longer watching when that change happens.

    The extra ``DELIVERED`` guard below covers the corner case where a
    screen is put back on the watch list after the food already left: it
    then removes itself again without printing a stale ticket.
    """

    def __init__(self, printer: Printer = print) -> None:
        self._printer = printer

    def update(self, order: Order) -> None:
        """Show the new status on the kitchen display."""
        if order.status is OrderStatus.DELIVERED:
            # Already gone - drop the watch quietly instead of printing.
            order.remove_watcher(self)
            return

        self._printer(f"Kitchen screen: {order.status.value}")

        if order.status is OrderStatus.OUT_FOR_DELIVERY:
            # The food has left the kitchen: the screen stops watching, so it
            # is not notified about anything that happens afterwards.
            order.remove_watcher(self)
