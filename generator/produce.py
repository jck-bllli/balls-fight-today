#!/usr/bin/env python3
"""Render every planned matchup that is not queued yet; append it to queue.json.

  python generator/produce.py --new            # render all missing
  python generator/produce.py --only race_0001 --dry-run   # render to generator/out, touch no queue
"""
import json
import os
import sys
import time

import engine
import render

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    only = args[args.index("--only") + 1] if "--only" in args else None
    plans = json.load(open(os.path.join(HERE, "matchups.json")))
    qpath = os.path.join(ROOT, "queue.json")
    queue = json.load(open(qpath))
    have = {q["id"] for q in queue}
    outdir = os.path.join(HERE, "out") if dry else os.path.join(ROOT, "videos")
    os.makedirs(outdir, exist_ok=True)
    for m in plans:
        if only and m["id"] != only:
            continue
        if not only and m["id"] in have:
            continue
        t0 = time.time()
        scale = engine.fit_scale(m["a"], m["b"], m["mode"])
        sim = engine.simulate(m["a"], m["b"], engine.layers_for(scale), m["mode"])
        if sim["winner"] is None:
            print(f"::error::{m['id']} has no winner, skipping")
            continue
        out = os.path.join(outdir, m["id"] + ".mp4")
        render.render(sim, out, style=m["style"])
        print(f"{m['id']} rendered in {time.time() - t0:.0f}s: {out}")
        if not dry:
            queue.append({"id": m["id"], "video": f"videos/{m['id']}.mp4", "caption": m["caption"],
                          "style": m["style"], "mode": m["mode"], "voice": "none", "thumb_offset_ms": 1000})
            json.dump(queue, open(qpath, "w"), indent=1)
    if dry:
        print(f"Dry run done. Output in {outdir}")


if __name__ == "__main__":
    main()
