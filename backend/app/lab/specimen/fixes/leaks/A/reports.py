"""Report loader for the lab dashboard."""
import json


def load_report(path):
    with open(path) as f:
        return json.load(f)


def summarize(paths):
    return [load_report(p)["title"] for p in paths]
