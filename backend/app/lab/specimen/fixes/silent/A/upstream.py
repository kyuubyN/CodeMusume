"""Pricing client for the checkout service."""
import json
import time
import urllib.request

PRICING_URL = "http://127.0.0.1:8765"


class PricingUnavailable(Exception):
    """The pricing service could not answer; never guess a price."""


def fetch_price(sku, retries=2):
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(f"{PRICING_URL}/price/{sku}", timeout=0.25) as resp:
                return json.load(resp)["price"]
        except (OSError, ValueError) as err:  # URLError, HTTPError and timeouts are OSErrors
            last_error = err
            time.sleep(0.02 * 2**attempt)
    raise PricingUnavailable(sku) from last_error


def cart_total(skus):
    return sum(fetch_price(sku) for sku in skus)
