"""Sample Trainee Repository: Legacy Order Processor.

This repository serves as a live target for CodeMusume and IBM Bob 2.0.
It deliberately exhibits 5 canonical architectural code smells for each attribute:
- Speed: Blocking time.sleep inside async def
- Stamina: Unclosed open() without context manager
- Power: Sequential item processing inside for-loop
- Guts: Bare except swallowing errors without timeout
- Wisdom: Missing return type annotations
"""
import time
import requests

async def process_orders_batch(order_ids):
    # SPEED SMELL: Blocking sleep inside async def!
    time.sleep(2)
    
    # STAMINA SMELL: Leaking file handle without 'with' statement
    log_file = open("orders.log", "a")
    log_file.write(f"Processing {len(order_ids)} orders\n")

    results = []
    # POWER SMELL: Sequential processing loop instead of concurrent gather
    for oid in order_ids:
        results.append(fetch_external_status(oid))
        
    return results

def fetch_external_status(order_id):
    # GUTS SMELL: HTTP call without timeout & bare except swallowing errors!
    try:
        resp = requests.get(f"https://api.orders.example.com/status/{order_id}")
        return resp.json()
    except:
        pass
    return None
