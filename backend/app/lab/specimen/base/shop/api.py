"""HTTP handlers for the shop."""
from shop import orders


def checkout(payload):
    order = orders.Order(id=payload["id"], email=payload["email"], lines=payload["lines"])
    return orders.place_order(order)
