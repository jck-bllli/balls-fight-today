"""Automatic daily ball race: pick a fresh matchup, find a near tie, render it, queue it.

No Claude needed per video. Run on the home PC:
    python daily.py --count 1            # render the next video(s) into queue/
    python daily.py --survey             # headless: which pairs can make a near tie
State lives in state.json (pairs used, pairs that never tie). Each queued item
gets a "style" key (the pair) so Otto can rank matchups once the account posts.
"""
import argparse
import itertools
import json
import os
import random

import ballsim as bs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QUEUE = os.path.join(ROOT, "videos")
QUEUE_JSON = os.path.join(ROOT, "queue.json")
STATE = os.path.join(HERE, "state.json")
MAX_GAP = 0.35          # seconds; a finish further apart than this is not close enough
COOLDOWN = 10           # don't repeat a pair within this many videos
PALETTE = ["red", "blue", "green", "gold", "pink"]


def load():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"history": [], "bad": [], "n": 0}


def save(st):
    with open(STATE, "w") as f:
        json.dump(st, f, indent=1)


def pairs():
    ps = [f"{a}__{b}" for a, b in itertools.combinations(sorted(bs.RULES), 2)]
    random.Random(7).shuffle(ps)
    return ps


def spec_for(pair, n):
    a, b = pair.split("__")
    ra, rb = dict(bs.RULES[a]), dict(bs.RULES[b])
    rnd = random.Random(n)
    if rnd.random() < 0.5:                       # random top / bottom
        ra, rb = rb, ra
    if ra["color"] == rb["color"]:
        rb["color"] = rnd.choice([c for c in PALETTE if c != ra["color"]])
    return {"rules": (ra, rb)}


def eligible(p, mode):
    """Comeback modes need a steady ball (it starts far ahead and gets caught); photo finishes work for any pair."""
    if mode in ("split", "late"):
        return any(bs.RULES[x].get("calibrate") for x in p.split("__"))
    return True


def next_pair(st, mode):
    recent = [h["pair"] for h in st["history"][-COOLDOWN:]]
    ok = [p for p in pairs() if eligible(p, mode) and f"{p}|{mode}" not in st["bad"]]
    for p in ok:
        if p not in recent:
            yield p
    for p in ok:                                  # everything used recently: allow repeats
        yield p


def caption(ra, rb):
    return (f"{ra['name'].title()} vs {rb['name'].title()}. Which one finishes first? "
            "Comment your pick before the end.\n\nFollow @ballsfighttoday for a new race every day.\n\n#ballsimulation #satisfying #physics #math #simulation")


def make_one(st, force_pair="", force_mode=""):
    mode = force_mode or bs.MIX[st["n"] % len(bs.MIX)]
    for pair in ([force_pair] if force_pair else next_pair(st, mode)):
        uses = sum(1 for h in st["history"] if h["pair"] == pair)
        spec, found = bs.tune_search(spec_for(pair, st["n"]), offset=uses * 3000, mode=mode)
        if not found:
            if uses == 0:
                st["bad"].append(f"{pair}|{mode}")
            print("skip", pair, mode)
            save(st)
            continue
        st["n"] += 1
        key = f"ball_{st['n']:04d}"
        out = bs.make_video(key, QUEUE, spec=spec, found=found)
        ra, rb = spec["rules"]
        item = {"file": os.path.basename(out), "caption": caption(ra, rb), "style": pair,
                "names": [ra["name"], rb["name"]], "mode": mode, "winner": 0 if found["ta"] < found["tb"] else 1, "gap": round(found["gap"], 3), "comeback": round(found["comeback"], 3),
                "seconds": round(max(found["ta"], found["tb"]) + 3, 1)}
        with open(QUEUE_JSON) as f:
            q = json.load(f)
        q.append({"id": key, "video": f"videos/{key}.mp4", "caption": item["caption"], "style": pair, "mode": mode,
                  "voice": "none", "gap": item["gap"], "thumb_offset_ms": 1000})
        with open(QUEUE_JSON, "w") as f:
            json.dump(q, f, indent=1)
        st["history"].append({"pair": pair, "key": key, "gap": item["gap"]})
        save(st)
        return item
    raise SystemExit(f"::error::no pair produced a {mode} result")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--test", action="store_true", help="render one video to generator/out, touch no state or queue")
    ap.add_argument("--pair", default="", help="force a pair, e.g. speedup__steady (sorted names)")
    ap.add_argument("--mode", default="", help="force a result mode: split, late or photo")
    a = ap.parse_args()
    if a.survey:
        for p in pairs():
            row = [p]
            for m in bs.MODES:
                _, f = bs.tune_search(spec_for(p, 0), tries=10, mode=m)
                row.append(f"{m}={f and round(f['gap'], 2)}")
            print(*row)
            continue
            print(p, f and round(f["gap"], 3), f and round(f["comeback"], 3))
    elif a.test:
        st = load()
        QUEUE = os.path.join(HERE, "out")
        QUEUE_JSON = os.path.join(QUEUE, "queue_test.json")
        os.makedirs(QUEUE, exist_ok=True)
        with open(QUEUE_JSON, "w") as f:
            f.write("[]")
        save = lambda st: None
        print(json.dumps(make_one(st, a.pair, a.mode)))
        print(f"Dry run done. Output in {QUEUE}")
    else:
        st = load()
        for _ in range(a.count):
            print(json.dumps(make_one(st)))
