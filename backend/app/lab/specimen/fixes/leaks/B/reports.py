"""Report loader for the lab dashboard."""
import json


def load_report(path):
    f = open(path)
    try:
        return json.load(f)
    finally:
        f.close()


def summarize(paths):
    return [load_report(p)["title"] for p in paths]
