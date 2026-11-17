"""Ball race simulation. Pure Python, no rendering.

Two balls bounce in their own lanes. Every wall bounce deals damage to the current HP layer
(there are 3 layers). First ball to break all layers wins. Damage grows by each ball's own rule.
Comeback modes help the trailing ball so the finish stays close.
"""
import math

# name -> (title, damage(n) for bounce n starting at 1, seconds between bounces at start)
BALLS = {
    "fibonacci": ("FIBONACCI BALL", lambda n, total=0: _fib(n), 0.50),
    "doubling": ("DOUBLING BALL", lambda n, total=0: 2 ** (n - 1), 0.50),
    "steady": ("STEADY BALL", lambda n, total=0: total // 90, 0.50),
    "cube": ("CUBE BALL", lambda n, total=0: n ** 3, 0.50),
    "compound": ("COMPOUND BALL", lambda n, total=0: int(1.5 ** (n - 1)), 0.50),
    "fast": ("FAST BALL", lambda n, total=0: 3 * n, 0.12),
    "strong": ("STRONG BALL", lambda n, total=0: 400 * n * n, 1.40),
    "square": ("SQUARE BALL", lambda n, total=0: n * n, 0.45),
}
_fibs = [1, 1]


def _fib(n):
    while len(_fibs) < n:
        _fibs.append(_fibs[-1] + _fibs[-2])
    return _fibs[n - 1]


MODES = ["none", "catchup", "second_wind"]
MODE_TEXT = {
    "none": "No help. Pure math.",
    "catchup": "COMEBACK: the trailing ball bounces faster.",
    "second_wind": "COMEBACK: the trailing ball hits harder.",
}


def layers_for(scale):
    base = scale
    return [base, base * 100, base * 10000]


def progress(hp, layers):
    """0..3: layers broken plus fraction of the current one."""
    done = 0.0
    for i, full in enumerate(layers):
        if hp[i] <= 0:
            done += 1
        else:
            done += 1 - hp[i] / full
            break
    return done


def simulate(a, b, layers, mode="none", dt=1 / 30, max_seconds=75):
    """Returns dict with per-frame state lists. Winner is whoever breaks layer 3 first."""
    names = [a, b]
    hp = [list(layers), list(layers)]
    nbounce = [0, 0]
    next_t = [BALLS[a][2] * 0.5, BALLS[b][2] * 0.5]
    frames, events = [], []
    t, winner = 0.0, None
    last_hit = [0, 0]
    while t < max_seconds and winner is None:
        for i in (0, 1):
            while next_t[i] <= t and winner is None:
                me, other = progress(hp[i], layers), progress(hp[1 - i], layers)
                behind = max(0.0, other - me)
                n = nbounce[i] + 1
                dmg = BALLS[names[i]][1](n, sum(layers))
                interval = BALLS[names[i]][2]
                if mode == "second_wind" and behind > 0.15:
                    dmg = int(dmg * (1 + min(behind, 1.0) * 2))
                if mode == "catchup" and behind > 0.15:
                    interval = interval / (1 + min(behind, 1.0) * 1.5)
                nbounce[i] = n
                last_hit[i] = dmg
                events.append((next_t[i], i, dmg, progress(hp[i], layers)))
                rem = dmg
                for k in range(3):
                    if hp[i][k] > 0:
                        take = min(rem, hp[i][k])
                        hp[i][k] -= take
                        rem -= take
                        if rem <= 0:
                            break
                if hp[i][2] <= 0:
                    winner = i
                next_t[i] += interval
        frames.append({"t": t, "hp": [list(hp[0]), list(hp[1])], "n": list(nbounce), "dmg": list(last_hit)})
        t += dt
    return {"names": names, "layers": layers, "frames": frames, "events": events,
            "winner": winner, "duration": t, "mode": mode}


def fit_scale(a, b, mode, target=48.0):
    """Pick the base HP so the race lasts about `target` seconds."""
    lo, hi = 1, 10 ** 32
    for _ in range(40):
        mid = int(math.exp((math.log(lo) + math.log(hi)) / 2)) or 1
        d = simulate(a, b, layers_for(mid), mode, dt=0.05, max_seconds=200)["duration"]
        if d < target:
            lo = mid + 1
        else:
            hi = mid
        if lo >= hi:
            break
    return lo
