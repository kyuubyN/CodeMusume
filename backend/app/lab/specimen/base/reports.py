"""Report loader for the lab dashboard."""
import json


def load_report(path):
    f = open(path)
    data = json.load(f)
    f.close()
    return data


def summarize(paths):
    return [load_report(p)["title"] for p in paths]
