"""Round the venue dump to centimetres to keep site/kino/venue.json small. Reads stdin, writes stdout."""
import json
import sys


def rnd(v):
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, list):
        return [rnd(x) for x in v]
    if isinstance(v, dict):
        return {k: rnd(x) for k, x in v.items()}
    return v


json.dump(rnd(json.load(sys.stdin)), sys.stdout, separators=(",", ":"))
