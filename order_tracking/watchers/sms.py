"""The SMS watcher - the customer's phone."""

from __future__ import annotations

from typing import Callable

from ..order import Order
from ..watcher import Watcher

Printer = Callable[[str], None]


class SmsNotifier(Watcher):
    """Sends a short message to the customer's phone on every change."""

    def __init__(
        self,
        recipient: str,
        printer: Printer = print,
        template: str = "SMS to {recipient}: your order is now {status}",
    ) -> None:
        self._recipient = recipient
        self._printer = printer
        self._template = template

    @property
    def recipient(self) -> str:
        """Who the messages are addressed to."""
        return self._recipient

    def update(self, order: Order) -> None:
        """Text the customer about the new status."""
        self._printer(
            self._template.format(
                recipient=self._recipient,
                status=order.status.value,
            )
        )
