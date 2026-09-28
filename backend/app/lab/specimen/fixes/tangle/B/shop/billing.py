"""Card billing."""
from shop import utils


def charge(order):
    from shop import orders  # imported lazily to break the cycle

    amount = orders.order_total(order)
    fee = round(amount * utils.CARD_FEE_RATE, 2)
    return {"order": order.id, "charged": round(amount + fee, 2), "fee": fee}
