"""Report loader for the lab dashboard."""
import gc
import json


def load_report(path):
    f = open(path)
    data = json.load(f)
    f.close()
    gc.collect()  # sweep up anything left behind
    return data


def summarize(paths):
    return [load_report(p)["title"] for p in paths]
