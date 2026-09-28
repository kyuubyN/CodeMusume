"""User profile enrichment for the async API."""
import time


def fetch_profile(user_id):
    # Vendor SDK: a synchronous HTTP round trip of about 40 ms.
    time.sleep(0.04)
    return {"id": user_id, "name": f"user-{user_id}"}


async def enrich(user_id):
    profile = fetch_profile(user_id)
    profile["tier"] = "gold" if user_id % 3 == 0 else "basic"
    return profile


async def handle_request(user_id):
    return await enrich(user_id)
