"""Gravity ball race videos, kept very simple.

Two boxes, one ball each. The ball falls under gravity and every bounce on
the floor deals damage to the top HP bar. Bars break one by one; when the
last one breaks the ball drops out and that ball is done. Each ball has its
own damage rule. The script tries many seeded runs headless, keeps the one
with the closest finish (lead must change hands), then renders that run.

    python ballsim.py --video all --out out
    python ballsim.py --video fib_vs_doubling --search-only
"""
import argparse
from decimal import Decimal
import json
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

W, H, FPS = 1080, 1920, 30
SUB = 4
DT = 1.0 / (FPS * SUB)
G = 1500.0                     # gravity px/s^2
BX, BW = 60, 960               # box x and width
PLAY_H = 420                   # open area above the bars
BAR_H = 88
CHECK_H = 28
TOP = (130, 970)               # box top y for ball A and ball B

BG = (220, 208, 182)
BOX = (250, 246, 236)
INK = (20, 20, 20)
COLORS = {"red": (214, 72, 40), "blue": (36, 104, 168), "green": (52, 132, 60), "gold": (204, 140, 20),
          "pink": (214, 76, 128)}

RULES = {
    "fib": dict(name="FIBONACCI BALL", color="red", op="fib", r=26, apex=(200, 320)),
    "doubling": dict(name="DOUBLING BALL", color="blue", op="mul", k=2, r=26, apex=(200, 330)),
    "grower": dict(name="GROWING BALL", color="gold", op="add", k=1, r=16, apex=(230, 350), grow=1.0, rmax=110),
    "splitter": dict(name="SPLITTING BALL", color="green", op="const", d0=1, r=12, apex=(220, 350), split=40),
    "fast": dict(name="FAST BALL", color="red", op="add", k=1, r=16, apex=(50, 110)),
    "strong": dict(name="STRONG BALL", color="blue", op="pow", k=2, r=40, apex=(320, 380)),
    # extra archetypes for the automatic daily picker
    "tripling": dict(name="TRIPLING BALL", color="pink", op="mul", k=3, r=30, apex=(300, 400)),
    "squares": dict(name="SQUARE BALL", color="green", op="pow", k=2, r=24, apex=(220, 340)),
    "cube": dict(name="CUBE BALL", color="gold", op="pow", k=3, r=28, apex=(260, 380)),
    "counting": dict(name="COUNTING BALL", color="blue", op="add", k=1, r=20, apex=(110, 210)),
    "shrinking": dict(name="SHRINKING BALL", color="pink", op="add", k=2, r=70, apex=(200, 320),
                      grow=-0.6, rmin=8, rmax=70),
    # steady balls: same damage every bounce, calibrated per matchup so a convex ball catches them at the very end
    "steady": dict(name="STEADY BALL", color="green", op="const", d0=1, r=24, apex=(220, 340), calibrate=True),
    "steady_fast": dict(name="QUICK STEADY BALL", color="red", op="const", d0=1, r=14, apex=(70, 150), calibrate=True),
    "heavy": dict(name="HEAVY BALL", color="gold", op="add", k=5, r=60, apex=(330, 390)),
    # ---- variety pack (Jack 2026-11-17): movement traits ----
    "speedup": dict(name="SPEEDING UP BALL", color="red", op="add", k=1, r=20, apex=(330, 380), speedup=0.975, apex_min=25),
    "slowdown": dict(name="SLOWING DOWN BALL", color="blue", op="add", k=3, r=22, apex=(60, 100), speedup=1.03, apex_min=25),
    "moon": dict(name="MOON BALL", color="gold", op="mul", k=2, r=26, apex=(250, 360), gscale=0.35),
    "superbouncy": dict(name="SUPER BOUNCY BALL", color="pink", op="pow", k=2, r=18, apex=(40, 70), speedup=1.08, apex_min=25),
    "sticky": dict(name="STICKY BALL", color="green", op="mul", k=2, r=26, apex=(220, 330), stick=0.45),
    "chaos": dict(name="CHAOS BALL", color="red", op="add", k=2, r=22, apex=(40, 370), chaos=True),
    "doublejump": dict(name="DOUBLE JUMP BALL", color="blue", op="fib", r=24, apex=(300, 370), pattern=(0.15, 0.15, 1.0)),
    "walls": dict(name="WALL BANGER BALL", color="gold", op="add", k=1, r=22, apex=(200, 320), walls=True),
    "twin": dict(name="TWIN BALL", color="pink", op="pow", k=2, r=18, apex=(220, 340), twin=30.0),
    "swarm": dict(name="SWARM BALL", color="green", op="add", k=1, r=14, apex=(220, 340), split=40, split_every=10),
    # ---- variety pack: damage rules ----
    "prime": dict(name="PRIME BALL", color="blue", op="prime", r=24, apex=(200, 330)),
    "factorial": dict(name="FACTORIAL BALL", color="red", op="fact", r=30, apex=(330, 390)),
    "lucky": dict(name="LUCKY BALL", color="gold", op="crit", k=2, r=22, apex=(150, 280), crit=(0.1, 10)),
    "fifth": dict(name="EVERY FIFTH BALL", color="pink", op="every", k=1, r=22, apex=(150, 280), every=(5, 25)),
    "combo": dict(name="COMBO BALL", color="green", op="combo", r=20, apex=(300, 370), speedup=0.96, apex_min=25, window=1.0),
    "sizehit": dict(name="BIG HIT BALL", color="red", op="size", r=14, apex=(220, 340), grow=1.0, rmax=110),
    "impact": dict(name="IMPACT BALL", color="blue", op="impact", r=22, apex=(40, 70), speedup=1.05, apex_min=25),
    "gambler": dict(name="GAMBLER BALL", color="gold", op="gamble", r=22, apex=(120, 260)),
    "fading": dict(name="FADING BALL", color="pink", op="fade", d0=300, k=0.96, floor_dmg=8, r=26, apex=(200, 330)),
}

# layers: HP of the 3 bars as fractions of the bottom bar (top bar breaks first)
VIDEOS = {
    "fib_vs_doubling": dict(balls=("fib", "doubling"), layers=(1e-12, 1e-5, 1)),
    "grower_vs_splitter": dict(balls=("grower", "splitter"), layers=(0.01, 0.1, 1)),
    "fast_vs_strong": dict(balls=("fast", "strong"), layers=(0.01, 0.1, 1)),
}
TARGET = 62.0
DMG_CAP = 500          # max damage per bounce of a steady ball (first hit has to look believable)
NICE = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5]


def fmt(n):
    """Exact below 1e15; above that keep 3 significant digits and zero-fill, so big numbers look clean
    (floats cannot hold 20+ digits, which used to show random digits at the end)."""
    n = float(n)
    if n < 1e15:
        return f"{int(round(n)):,}"
    return f"{int(Decimal(f'{n:.3g}')):,}"


def _primes(n, _c=[2]):
    k = _c[-1]
    while len(_c) < n:
        k += 1
        if all(k % p for p in _c if p * p <= k):
            _c.append(k)
    return _c[n - 1]


class Ball:
    def __init__(self, rule, seed):
        self.rule = rule
        self.rng = np.random.default_rng(seed)
        self.g = G * rule.get("gscale", 1.0)
        r = rule["r"]
        self.r = float(r)
        n0 = 2 if rule.get("twin") else 1
        self.pos = np.array([[self.rng.uniform(r + 40, BW - r - 40), self.rng.uniform(r + 10, 120)] for _ in range(n0)])
        self.vel = np.array([[self.rng.uniform(140, 320) * self.rng.choice([-1, 1]), 0.0] for _ in range(n0)])
        self.v0 = np.array([self._launch() for _ in range(n0)])
        self.vbase = self.v0.copy()
        self.wait = np.zeros(n0)
        self.bnc = np.zeros(n0, dtype=int)
        self.hits = 0
        self.dmg = float(rule.get("d0", 1))
        self.fib = (0, 1)
        self.cum = 0.0
        self.floor = PLAY_H
        self.done = False
        self.t = 0.0
        self.last_hit = -9.0
        self.combo = 0
        self.merged = False

    def _launch(self):
        return math.sqrt(2 * self.g * self.rng.uniform(*self.rule["apex"]))

    def _next(self, i=0):
        op = self.rule["op"]
        self.hits += 1
        n = self.hits
        k = self.rule.get("k", 1)
        if op == "pow":
            self.dmg = float(n ** k)
        elif op == "mul":
            self.dmg = 1.0 if n == 1 else self.dmg * k
        elif op == "add":
            self.dmg = 1.0 + (n - 1) * k
        elif op == "fib":
            a, b = self.fib
            self.fib = (b, a + b)
            self.dmg = float(b)
        elif op == "prime":
            self.dmg = float(_primes(n))
        elif op == "fact":
            self.dmg = float(math.factorial(min(1 + (n - 1) // 3, 150)))  # slow factorial: steps up every 3rd hit
        elif op == "crit":
            p, m = self.rule["crit"]
            self.dmg = (1.0 + (n - 1) * k) * (m if self.rng.random() < p else 1)
        elif op == "every":
            every, m = self.rule["every"]
            self.dmg = (1.0 + (n - 1) * k) * (m if n % every == 0 else 1)
        elif op == "combo":
            self.combo = self.combo + 1 if self.t - self.last_hit < self.rule.get("window", 0.6) else 1
            self.dmg = float(self.combo ** 2)
        elif op == "size":
            self.dmg = float(round(self.r ** 2 / 10))
        elif op == "impact":
            h = self.v0[i] ** 2 / (2 * self.g)
            self.dmg = float(max(1, round(h * h / 100)))
        elif op == "gamble":
            self.dmg = 1.0 if n == 1 else (self.dmg * 3 if self.rng.random() < 0.5 else max(1.0, self.dmg / 2))  # win: x3, lose: half
        elif op == "fade":
            self.dmg = float(max(self.rule.get("floor_dmg", 1), round(self.rule["d0"] * k ** (n - 1))))
        self.last_hit = self.t
        return self.dmg

    def _relaunch(self, idx):
        """New bounce speed after a floor hit, per movement trait."""
        ru = self.rule
        top = max(30.0, PLAY_H - 20 - self.r)
        for i in idx:
            self.bnc[i] += 1
            if ru.get("chaos"):
                self.v0[i] = self._launch()
            elif ru.get("pattern"):
                pat = ru["pattern"]
                self.v0[i] = self.vbase[i] * math.sqrt(pat[self.bnc[i] % len(pat)])
            elif ru.get("speedup"):
                h = self.v0[i] ** 2 / (2 * self.g) * ru["speedup"]
                h = min(max(h, ru.get("apex_min", 20)), top if self.g >= G else 10 ** 9)
                self.v0[i] = math.sqrt(2 * self.g * h)

    def step(self, events=None, t=0.0):
        self.t += DT
        ru = self.rule
        if ru.get("twin") and not self.merged and self.t >= ru["twin"] and len(self.pos) > 1:
            self.merged = True  # the two halves join into one bigger ball
            keep = [0]
            self.pos, self.vel, self.v0 = self.pos[keep], self.vel[keep], self.v0[keep]
            self.vbase, self.wait, self.bnc = self.vbase[keep], self.wait[keep], self.bnc[keep]
            self.r *= 1.5
        p, v, r = self.pos, self.vel, self.r
        moving = self.wait <= 0
        v[moving, 1] += self.g * DT
        p[moving] += v[moving] * DT
        if ru.get("stick"):
            w = self.wait > 0
            self.wait[w] -= DT
            rel = w & (self.wait <= 0)
            v[rel, 1] = -self.v0[rel]
        lo = p[:, 0] < r
        hi = p[:, 0] > BW - r
        p[lo, 0] = r
        p[hi, 0] = BW - r
        v[lo | hi, 0] *= -1
        top = p[:, 1] < r
        p[top, 1] = r
        v[top, 1] = np.abs(v[top, 1])
        if self.done:
            return
        hit = (p[:, 1] > self.floor - r) & (v[:, 1] > 0)
        wall_idx = np.nonzero(lo | hi)[0] if ru.get("walls") else np.array([], dtype=int)
        if not hit.any() and not len(wall_idx):
            return
        idx = np.nonzero(hit)[0]
        p[idx, 1] = self.floor - r
        if ru.get("stick"):
            v[idx, 1] = 0.0
            self.wait[idx] = ru["stick"]
        all_idx = np.concatenate([idx, wall_idx]).astype(int)
        k = len(all_idx)
        if self.rule["op"] == "const":
            self.hits += k
            dealt = [self.dmg] * k
            self.cum += self.dmg * k
        else:
            dealt = [self._next(i) for i in all_idx]
            self.cum += sum(dealt)
        self._relaunch(idx)
        if not ru.get("stick"):
            v[idx, 1] = -self.v0[idx]
        if events is not None:
            for i, dv in zip(all_idx[:2], dealt[:2]):
                events.append((t, float(p[i, 0]), float(min(p[i, 1] + r, self.floor)), dv))
        if not len(idx):
            return
        if self.rule.get("grow"):
            self.r = min(self.rule["rmax"], max(self.rule.get("rmin", 4), self.r + self.rule["grow"] * len(idx)))
        cap = self.rule.get("split")
        if cap and len(p) < cap:
            every = self.rule.get("split_every", 1)
            spawn = self.hits // every - (self.hits - len(idx)) // every
            if spawn <= 0:
                return
            sidx = np.resize(idx, spawn)[: cap - len(p)]
            nv = v[sidx].copy()
            nv[:, 0] = self.rng.uniform(140, 360, len(sidx)) * self.rng.choice([-1, 1], len(sidx))
            self.pos = np.vstack([p, p[sidx]])
            self.vel = np.vstack([v, nv])
            nl = np.array([self._launch() for _ in sidx])
            self.v0 = np.concatenate([self.v0, nl])
            self.vbase = np.concatenate([self.vbase, nl])
            self.wait = np.concatenate([self.wait, np.zeros(len(sidx))])
            self.bnc = np.concatenate([self.bnc, np.zeros(len(sidx), dtype=int)])


def curve(rule, seed, seconds):
    b = Ball(rule, seed)
    n = int(seconds / DT)
    out = np.empty(n)
    for i in range(n):
        b.step()
        out[i] = b.cum
    return out


def auto_layers(m, e):
    """Ref style: small top bar, middle bar, huge bottom bar (1,000 / 10B / 1e15)."""
    a = max(1, round(e * 0.2))
    b = max(a + 1, round(e * 0.67))
    if b >= e:
        b = e - 1
    return [m * 10 ** a, m * 10 ** b, m * 10 ** e]


def layer_sets(spec, lo, hi):
    f = spec.get("layers")
    e = max(2, int(math.floor(math.log10(max(lo, 1)))) - 1)
    while True:
        for m in NICE:
            l3 = m * 10 ** e
            layers = [max(1.0, round(l3 * x)) for x in f] if f else auto_layers(m, e)
            tot = sum(layers)
            if tot > hi:
                return
            if tot >= lo:
                yield layers, tot
        e += 1


def rules_of(spec):
    return spec.get("rules") or tuple(RULES[k] for k in spec["balls"])


MODES = {
    # gap range (s), minimum comeback (winner's mid-race deficit as a share of total HP)
    "split": dict(gap=(0.04, 0.35), comeback=0.04),   # obvious loser steals it by a split second
    "late": dict(gap=(1.0, 3.0), comeback=0.04),      # the mid-race leader loses by 1 to 3 seconds (3s = the clearest win allowed)
    "photo": dict(gap=(0.04, 0.20), comeback=-1.0),   # plain photo finish, lead swaps
}
MIX = ["split", "split", "late", "split", "photo", "late", "split"]   # per-video rotation, keeps the profile unpredictable


def round_sig(x, n=2):
    if x <= 0:
        return 1
    e = math.floor(math.log10(x)) - (n - 1)
    return max(1, int(round(x / 10 ** e) * 10 ** e))


def search(spec, tries=160, offset=0, mode="split"):
    ra, rb = rules_of(spec)
    mcfg = MODES[mode]
    win = (TARGET - 7, TARGET + 7)
    best = None
    i0, i1 = int(win[0] / DT), int(win[1] / DT)
    for s in range(tries):
        sa, sb = 1000 + offset + s * 7, 5000 + offset + s * 13
        ca, cb = curve(ra, sa, win[1] + 4), curve(rb, sb, win[1] + 4)
        # calibrated (steady) ball: try several damage-per-hit values so it crosses its partner near the finish
        cands = [(None, None, ca, cb)]
        if ra.get("calibrate") != rb.get("calibrate"):
            sa_is_cal = bool(ra.get("calibrate"))
            hits = ca if sa_is_cal else cb
            other = cb if sa_is_cal else ca
            cands = []
            for tc in np.arange(win[0] + 1, win[1] - 1, 1.5):
                j = int(tc / DT)
                if hits[j] <= 0 or other[j] <= 0:
                    continue
                d0 = round_sig(other[j] / hits[j])
                if d0 > DMG_CAP:                 # a first bounce must not hit for thousands
                    continue
                if sa_is_cal:
                    cands.append((d0, None, hits * d0, other))
                else:
                    cands.append((None, d0, other, hits * d0))
        for d0a, d0b, ca2, cb2 in cands:
            for layers, tot in layer_sets(spec, min(ca2[i0], cb2[i0]), max(ca2[i1], cb2[i1])):
                ta, tb = np.searchsorted(ca2, tot) * DT, np.searchsorted(cb2, tot) * DT
                if not (win[0] <= min(ta, tb) <= win[1]) or max(ta, tb) > win[1] + 3.9:
                    continue
                gap = abs(ta - tb)
                if not (mcfg["gap"][0] <= gap <= mcfg["gap"][1]):
                    continue
                i = int(min(ta, tb) / DT)
                loser_a = ta > tb
                d = (ca2[:i] - cb2[:i]) * (1 if loser_a else -1)
                swap = bool((d > 0).any())          # the loser led at some point
                # how far behind the eventual winner looks mid-race (log scale: exponential balls look level on a linear bar)
                la = np.log10(1.0 + np.maximum(ca2[:i], 0)) / math.log10(1.0 + tot)
                lb = np.log10(1.0 + np.maximum(cb2[:i], 0)) / math.log10(1.0 + tot)
                dl = (la - lb) * (1 if loser_a else -1)
                lo_i, hi_i = int(i * 0.5), int(i * 0.9)
                comeback = float(np.median(dl[lo_i:hi_i])) if hi_i > lo_i else 0.0
                if comeback < mcfg["comeback"] or not swap:
                    continue
                if mode == "photo":
                    score = gap
                elif mode == "late":
                    score = -4 * comeback + abs(gap - 2.0) * 0.1
                else:
                    score = gap - 4.0 * max(0.0, comeback)
                if best is None or score < best["score"]:
                    best = dict(score=score, seed_a=sa, seed_b=sb, layers=layers, total=tot, d0_a=d0a, d0_b=d0b,
                                ta=float(ta), tb=float(tb), gap=float(gap), swap=swap, comeback=comeback, mode=mode)
    return best


SCALES = (0.6, 0.8, 1.0, 1.25)   # bounce-height tuning; kept near 1 so balls still bounce high (Jack 2026-11-17)


def scaled(rule, f):
    lo, hi = rule["apex"]
    lo, hi = max(30.0, lo * f), min(400.0 - rule["r"], hi * f)
    return dict(rule, apex=(min(lo, hi - 4), hi))


def tune_search(spec, tries=12, offset=0, good=0.25, mode="split"):
    """Search bounce-height scales too, so any two ball types can be made to finish close."""
    ra, rb = rules_of(spec)
    best = None
    combos = sorted(((fa, fb) for fa in SCALES for fb in SCALES), key=lambda c: abs(c[0] - 1) + abs(c[1] - 1))
    for fa, fb in combos:
        sp = dict(spec, rules=(scaled(ra, fa), scaled(rb, fb)))
        f = search(sp, tries=tries, offset=offset, mode=mode)
        if f and (best is None or f["score"] < best[1]["score"]):
            best = (sp, dict(f, scale_a=fa, scale_b=fb))
        if best and (mode != "split" or best[1]["gap"] <= good) and best[1]["comeback"] >= (0.05 if mode != "photo" else -1):
            break
    return best or (spec, None)


# ---------- drawing ----------
def font(name, size, _c={}):
    if (name, size) not in _c:
        f = {"black": "NunitoBlack.woff", "bold": "NunitoExtraBold.woff"}[name]
        _c[(name, size)] = ImageFont.truetype(os.path.join(FONT_DIR, f), size)
    return _c[(name, size)]


CHECKER = None


def checker():
    global CHECKER
    if CHECKER is None:
        im = Image.new("RGB", (BW, CHECK_H), INK)
        d = ImageDraw.Draw(im)
        s = CHECK_H // 2
        for i in range(0, BW // s + 1):
            for j in range(2):
                if (i + j) % 2 == 0:
                    d.rectangle((i * s, j * s, i * s + s - 1, j * s + s - 1), fill=(255, 255, 255))
        CHECKER = im
    return CHECKER


def draw(img, balls, rules, layers, t, popups, banner):
    d = ImageDraw.Draw(img)
    for j, (b, ru) in enumerate(zip(balls, rules)):
        col = COLORS[ru["color"]]
        y0 = TOP[j]
        d.text((W // 2, y0 - 34), ru["name"], font=font("black", 46), fill=col, anchor="mm")
        bottom = y0 + PLAY_H + BAR_H * 3
        d.rectangle((BX - 4, y0 - 4, BX + BW + 4, bottom + 4), fill=INK)
        d.rectangle((BX, y0, BX + BW, y0 + min(b.floor, PLAY_H + BAR_H * 3)), fill=BOX)
        left = b.cum
        for li, hp in enumerate(layers):
            rem = hp - min(hp, left)
            left = max(0.0, left - hp)
            ty = y0 + PLAY_H + li * BAR_H
            if rem <= 0:
                d.rectangle((BX, ty, BX + BW, ty + BAR_H), fill=BOX)
                continue
            d.rectangle((BX, ty, BX + BW, ty + BAR_H - 4), fill=col)
            d.text((W // 2, ty + BAR_H // 2 - 2), fmt(rem), font=font("black", 40), fill=INK, anchor="mm")
        img.paste(checker(), (BX, bottom + 4))
        d.text((BX + 16, y0 + 14), "DAMAGE: " + fmt(b.dmg), font=font("black", 24), fill=col)
        for (pt, px, py, dv) in popups[j]:
            age = t - pt
            if 0 <= age < 0.7:
                c = tuple(int(a + (z - a) * age / 0.7) for a, z in zip(col, BOX))
                d.text((BX + px, y0 + py - 50 - age * 40), "-" + fmt(dv), font=font("bold", 26), fill=c, anchor="mm")
        for (px, py) in b.pos:
            x, y, r = BX + px, y0 + py, b.r
            if y - r > bottom + CHECK_H + 4:
                continue
            d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=INK, width=3 if r > 9 else 2)
    vy = (TOP[0] + PLAY_H + BAR_H * 3 + CHECK_H + TOP[1] - 34) // 2 + 4
    d.text((W // 2, vy), "VS", font=font("black", 44), fill=INK, anchor="mm")
    if banner:
        name, col, sub = banner
        d.rounded_rectangle((BX + 60, 760, BX + BW - 60, 1000), 24, fill=INK)
        d.text((W // 2, 840), name + " WINS", font=font("black", 58), fill=col, anchor="mm")
        d.text((W // 2, 930), sub, font=font("black", 42), fill=(255, 255, 255), anchor="mm")


# ---------- audio ----------
SR = 44100


def ping(freq, dur=0.08, amp=0.2):
    t = np.arange(int(SR * dur)) / SR
    return amp * np.sin(2 * np.pi * freq * t) * np.exp(-t * 45)


def crack(dur=0.25):
    t = np.arange(int(SR * dur)) / SR
    rng = np.random.default_rng(1)
    return 0.35 * rng.uniform(-1, 1, len(t)) * np.exp(-t * 18)


def add(audio, t, snd):
    i = int(t * SR)
    n = max(0, min(len(snd), len(audio) - i))
    audio[i:i + n] += snd[:n]


def make_video(key, outdir, search_only=False, spec=None, found=None):
    spec = spec or VIDEOS[key]
    found = found or search(spec)
    print(key, json.dumps(found))
    if search_only or not found:
        return
    ra, rb = rules_of(spec)
    if found.get("d0_a"):
        ra = dict(ra, d0=found["d0_a"])
    if found.get("d0_b"):
        rb = dict(rb, d0=found["d0_b"])
    rules = (ra, rb)
    layers = found["layers"]
    balls = [Ball(ra, found["seed_a"]), Ball(rb, found["seed_b"])]
    os.makedirs(outdir, exist_ok=True)
    vtmp = os.path.join(outdir, key + "_v.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                             "-crf", "18", "-pix_fmt", "yuv420p", vtmp], stdin=subprocess.PIPE)
    total = max(found["ta"], found["tb"]) + 6
    audio = np.zeros(int(total * SR))
    base = (330.0, 440.0)
    popups = ([], [])
    broken = [0, 0]
    finish = [None, None]
    t, n, end_t, banner = 0.0, 0, None, None
    while True:
        for _ in range(SUB):
            t += DT
            for j, b in enumerate(balls):
                ev = []
                b.step(ev, t)
                for e in ev:
                    popups[j].append(e)
                    add(audio, t, ping(base[j] * 2 ** (min(math.log10(e[3] + 1), 15) / 10)))
                while broken[j] < 3 and b.cum >= sum(layers[: broken[j] + 1]):
                    broken[j] += 1
                    b.floor = PLAY_H + BAR_H * broken[j] if broken[j] < 3 else 10 ** 9
                    add(audio, t, crack())
                if broken[j] == 3 and finish[j] is None:
                    finish[j] = t
                    b.done = True
        for j in range(2):
            popups[j][:] = [e for e in popups[j] if t - e[0] < 0.7][-10:]
        if all(f is not None for f in finish) and end_t is None:
            end_t = t
            w = 0 if finish[0] < finish[1] else 1
            banner = (rules[w]["name"], COLORS[rules[w]["color"]], f"BY {abs(finish[0] - finish[1]):.2f} SECONDS")
            add(audio, t, sum(ping(f, 1.2, 0.15) for f in (base[w], base[w] * 1.25, base[w] * 1.5)))
        img = Image.new("RGB", (W, H), BG)
        draw(img, balls, rules, layers, t, popups, banner)
        proc.stdin.write(img.tobytes())
        n += 1
        if end_t is not None and t - end_t > 3.0:
            break
    proc.stdin.close()
    proc.wait()
    secs = n / FPS
    wav = os.path.join(outdir, key + ".wav")
    with wave.open(wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(audio[: int(secs * SR)], -1, 1) * 32767).astype("<i2").tobytes())
    out = os.path.join(outdir, key + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vtmp, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "128k", "-shortest", out], check=True)
    os.remove(vtmp)
    os.remove(wav)
    with open(os.path.join(outdir, key + ".json"), "w") as fh:
        json.dump(found, fh, indent=1)
    print("wrote", out, f"{secs:.1f}s")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="all")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--search-only", action="store_true")
    a = ap.parse_args()
    for k in (list(VIDEOS) if a.video == "all" else [a.video]):
        make_video(k, a.out, a.search_only)
