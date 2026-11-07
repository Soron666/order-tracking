"""The states an order can be in.

Kept in its own module so that both the order and its watchers can talk
about a status without importing each other.
"""

from __future__ import annotations

from enum import Enum


class OrderStatus(Enum):
    """Every status a food-delivery order can move through."""

    PLACED = "Placed"
    COOKING = "Cooking"
    OUT_FOR_DELIVERY = "Out for delivery"
    DELIVERED = "Delivered"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
