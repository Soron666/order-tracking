"""Demonstration of the order tracker.

Running this module prints exactly the output required by the assignment:

    Order is now: Cooking
    SMS to Rahim: your order is now Cooking
    Kitchen screen: Cooking
    Order is now: Out for delivery
    SMS to Rahim: your order is now Out for delivery
    Kitchen screen: Out for delivery
    Order is now: Delivered
    SMS to Rahim: your order is now Delivered

The kitchen screen stops watching once the food has left the kitchen
(``Out for delivery``), which is why it is not notified about ``Delivered``.
"""

from __future__ import annotations

from .order import Order
from .status import OrderStatus
from .watchers.kitchen import KitchenScreen
from .watchers.sms import SmsNotifier


def build_demo_order() -> Order:
    """Create the order with the customer's phone and the kitchen screen."""
    order = Order(order_id="ORD-1001", status=OrderStatus.PLACED)

    # The order is given two watchers.  It has no idea what they are.
    order.add_watcher(SmsNotifier(recipient="Rahim"))
    order.add_watcher(KitchenScreen())

    return order


def main() -> None:
    """Run the order through its whole life."""
    order = build_demo_order()

    order.change_status(OrderStatus.COOKING)
    order.change_status(OrderStatus.OUT_FOR_DELIVERY)
    order.change_status(OrderStatus.DELIVERED)


if __name__ == "__main__":
    main()
