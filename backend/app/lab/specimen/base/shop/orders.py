"""Orders and their totals."""
from dataclasses import dataclass, field

from shop import billing, notifications, utils


@dataclass
class Order:
    id: int
    email: str
    lines: list = field(default_factory=list)  # (sku, qty, unit_price)
    created_at: str = field(default_factory=utils.now_iso)


def order_total(order):
    return round(sum(qty * price for _, qty, price in order.lines), 2)


def place_order(order):
    receipt = billing.charge(order)
    notifications.send_receipt(order.id, order.email, receipt["charged"])
    return receipt
