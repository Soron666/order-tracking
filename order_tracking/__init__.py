"""A small food-delivery order tracker built on the Observer pattern.

The order (:class:`~order_tracking.order.Order`) holds a status and a list of
watchers.  It never mentions phones or kitchens - it only announces
"my status changed" and lets the watchers decide how to report it.
"""

from .order import Order
from .status import OrderStatus
from .watcher import Watcher
from .watchers.kitchen import KitchenScreen
from .watchers.sms import SmsNotifier

__all__ = [
    "Order",
    "OrderStatus",
    "Watcher",
    "KitchenScreen",
    "SmsNotifier",
]

__version__ = "1.0.0"
