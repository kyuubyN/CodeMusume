"""Pricing client for the checkout service."""
import json
import logging
import urllib.request

PRICING_URL = "http://127.0.0.1:8765"
log = logging.getLogger(__name__)


def fetch_price(sku):
    try:
        with urllib.request.urlopen(f"{PRICING_URL}/price/{sku}") as resp:
            return json.load(resp)["price"]
    except Exception as err:
        log.warning("pricing failed for %s: %s", sku, err)
        return 0


def cart_total(skus):
    total = 0
    for sku in skus:
        price = fetch_price(sku)
        total += price or 0
    return total
