"""Pure pricing rules: depends on nothing else in the shop."""


def order_total(order):
    return round(sum(qty * price for _, qty, price in order.lines), 2)
