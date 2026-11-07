"""The watcher side of the contract.

A watcher is anything that wants to know when an order changes status.
The order never asks what kind of watcher it is talking to - it only
knows the small interface defined here.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .order import Order


class Watcher(abc.ABC):
    """Something that wants to be told about an order's status changes.

    Implementations decide for themselves *how* to report a change: an SMS,
    a screen, a log line, a push notification, and so on.
    """

    @abc.abstractmethod
    def update(self, order: "Order") -> None:
        """Called once per status change for every watcher on the list.

        The order hands itself over so a watcher can read ``order.status``
        and, if it wants to, remove itself with ``order.remove_watcher(self)``.
        """
