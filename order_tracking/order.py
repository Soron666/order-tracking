"""The order under watch.

The order holds a status and a list of watchers.  It has no idea what kind
of watcher it is talking to - it never refers to any particular reporting
channel.  All the order can do is say "my status changed" and let whoever
is watching react in their own way.
"""

from __future__ import annotations

import threading
from typing import Callable, List

from .status import OrderStatus
from .watcher import Watcher

Printer = Callable[[str], None]


class Order:
    """A single food-delivery order.

    Watchers can be added and removed at any moment, including while a
    status change is being broadcast.
    """

    def __init__(
        self,
        order_id: str = "ORD-1001",
        status: OrderStatus = OrderStatus.PLACED,
        printer: Printer = print,
    ) -> None:
        self._order_id = order_id
        self._status = status
        self._watchers: List[Watcher] = []
        self._lock = threading.RLock()
        self._printer = printer

    # ------------------------------------------------------------------
    # state
    # ------------------------------------------------------------------
    @property
    def order_id(self) -> str:
        """Identifier of the order."""
        return self._order_id

    @property
    def status(self) -> OrderStatus:
        """The status the order is in right now."""
        return self._status

    @property
    def watchers(self) -> List[Watcher]:
        """A snapshot of the current watcher list."""
        with self._lock:
            return list(self._watchers)

    # ------------------------------------------------------------------
    # the watch list
    # ------------------------------------------------------------------
    def add_watcher(self, watcher: Watcher) -> None:
        """Start watching this order.

        Adding the same watcher twice has no effect.
        """
        with self._lock:
            if watcher not in self._watchers:
                self._watchers.append(watcher)

    def remove_watcher(self, watcher: Watcher) -> None:
        """Stop watching this order.

        Removing a watcher that is not on the list has no effect.
        """
        with self._lock:
            if watcher in self._watchers:
                self._watchers.remove(watcher)

    # ------------------------------------------------------------------
    # the one thing that happens
    # ------------------------------------------------------------------
    def change_status(self, new_status: OrderStatus) -> None:
        """Move the order to ``new_status`` and tell every watcher once.

        The watcher list is copied before the broadcast, so the set of
        watchers notified is exactly the set that was watching at the
        moment of the change - even if a watcher adds or removes watchers
        (itself included) while it is being told.
        """
        with self._lock:
            self._status = new_status
            self._printer(f"Order is now: {new_status.value}")
            current_watchers = list(self._watchers)

        for watcher in current_watchers:
            watcher.update(self)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Order(order_id={self._order_id!r}, status={self._status.value!r})"
