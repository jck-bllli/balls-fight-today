"""Plan upcoming matchups: deterministic rotation of ball pairs, comeback modes and visual styles.

  python generator/plan.py 14      # append 14 new matchups to generator/matchups.json
"""
import itertools
import json
import os
import random
import sys

import engine

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "matchups.json")
STYLES = ["cream", "midnight", "mint"]  # visual styles Otto compares
HASHTAGS = "#ballrace #satisfying #math #simulation #marblerace #oddlysatisfying #whowins"


def valid(a, b, mode):
    s = engine.fit_scale(a, b, mode)
    r = engine.simulate(a, b, engine.layers_for(s), mode)
    return r["winner"] is not None and 35 < r["duration"] < 62


def pool():
    pairs = list(itertools.combinations(engine.BALLS, 2))
    return [(a, b, m) for (a, b) in pairs for m in engine.MODES]


def main(n):
    cur = json.load(open(PATH)) if os.path.exists(PATH) else []
    used = {(m["a"], m["b"], m["mode"]) for m in cur}
    cands = [c for c in pool() if c not in used]
    if len(cands) < n:  # everything used once: start a second lap
        used = set()
        cands = pool()
    # spread modes evenly: round robin through the mode list
    out = []
    i = len(cur)
    while len(out) < n and cands:
        mode = engine.MODES[i % 3]
        same = [c for c in cands if c[2] == mode]
        random.Random(f"ball{i}").shuffle(same)
        pick = next((c for c in same if valid(*c)), None)
        if pick is None:
            mode_c = [c for c in cands if valid(*c)]
            if not mode_c:
                break
            pick = mode_c[0]
        cands.remove(pick)
        a, b, m = pick
        title = f"{engine.BALLS[a][0].title()} vs {engine.BALLS[b][0].title()}"
        out.append({"id": f"race_{i + 1:04d}", "a": a, "b": b, "mode": m, "style": STYLES[i % 3],
                    "caption": f"{title}: who wins? 👇\nComment your pick before the end.\n"
                               f"{engine.MODE_TEXT[m]}\n\nFollow @ballsfighttoday for a new race every day.\n\n{HASHTAGS}"})
        i += 1
    json.dump(cur + out, open(PATH, "w"), indent=1)
    print(f"Planned {len(out)} matchups ({len(cur) + len(out)} total).")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
