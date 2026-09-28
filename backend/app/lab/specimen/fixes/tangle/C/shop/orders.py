"""Orders, their totals, and card billing (merged)."""
from dataclasses import dataclass, field

from shop import notifications, utils


@dataclass
class Order:
    id: int
    email: str
    lines: list = field(default_factory=list)  # (sku, qty, unit_price)
    created_at: str = field(default_factory=utils.now_iso)


def order_total(order):
    return round(sum(qty * price for _, qty, price in order.lines), 2)


def charge(order):
    amount = order_total(order)
    fee = round(amount * utils.CARD_FEE_RATE, 2)
    return {"order": order.id, "charged": round(amount + fee, 2), "fee": fee}


def place_order(order):
    receipt = charge(order)
    notifications.send_receipt(order.id, order.email, receipt["charged"])
    return receipt
