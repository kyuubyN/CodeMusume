# tachyon_lab

Dr. Tachyon's test subject: a small, working, and deeply unwell service.
Every module runs, and every module is sick in a way you can measure.

| Module | Symptom |
|---|---|
| `reports.py` | file handles survive their requests |
| `profiles.py` | the async API stalls under load |
| `orders.py` | the order page talks to the database far too often |
| `upstream.py` | checkout totals are sometimes silently wrong |
| `shop/` | testing billing drags in half the shop |
