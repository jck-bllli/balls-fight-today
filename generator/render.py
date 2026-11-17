"""Render one ball race to MP4 (1080x1920, 30 fps) with Pillow + ffmpeg."""
import bisect
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import engine

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
THEMES = {
    "cream": dict(bg=(220, 207, 176), arena=(250, 245, 233), ink=(20, 20, 20), a=(214, 69, 40), b=(36, 100, 176), ghost=(150, 140, 120)),
    "midnight": dict(bg=(18, 22, 38), arena=(30, 36, 60), ink=(240, 240, 250), a=(255, 99, 99), b=(90, 170, 255), ghost=(120, 130, 160)),
    "mint": dict(bg=(207, 232, 220), arena=(244, 252, 247), ink=(16, 40, 30), a=(232, 106, 51), b=(38, 120, 120), ghost=(120, 150, 135)),
}
_fonts = {}


def font(size, heavy=True):
    key = (size, heavy)
    if key not in _fonts:
        name = "NunitoBlack.woff" if heavy else "NunitoExtraBold.woff"
        try:
            _fonts[key] = ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
        except OSError:
            _fonts[key] = ImageFont.load_default()
    return _fonts[key]


def fmt(n):
    return f"{max(int(n), 0):,}"


def fit_text(d, xy, text, size, fill, maxw, anchor="mm"):
    while size > 14 and d.textlength(text, font=font(size)) > maxw:
        size -= 2
    d.text(xy, text, font=font(size), fill=fill, anchor=anchor)


def lane_events(events, i):
    return [e for e in events if e[1] == i]


def ball_xy(t, evs, times, box, rng_y, r):
    """Ball flies wall to wall; every event is a wall hit."""
    x0, y0, x1, y1 = box
    k = bisect.bisect_right(times, t) - 1
    left, right = x0 + r + 4, x1 - r - 4
    ys = lambda j: y0 + r + 10 + rng_y[j % len(rng_y)] * (y1 - y0 - 2 * r - 20)
    if k < 0:
        return (x0 + x1) / 2, y1 - r - 6
    nxt = times[k + 1] if k + 1 < len(times) else times[k] + 0.5
    p = min(max((t - times[k]) / max(nxt - times[k], 1e-3), 0), 1)
    xa, xb = (left, right) if k % 2 == 0 else (right, left)
    x = xa + (xb - xa) * p
    y = ys(k) + (ys(k + 1) - ys(k)) * p
    return x, y


def make_audio(sim, path, total):
    sr = 44100
    buf = np.zeros(int(sr * total) + sr)
    for (t, i, dmg, prog) in sim["events"]:
        f = 260 + prog * 380 + (60 if i else 0)
        n = int(sr * 0.05)
        tt = np.arange(n) / sr
        tick = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 60) * 0.35
        s = int(t * sr)
        buf[s:s + n] += tick[: len(buf) - s]
    ws = sim["duration"]
    for j, f in enumerate((523, 659, 784, 1047)):  # win jingle
        n = int(sr * 0.18)
        tt = np.arange(n) / sr
        s = int((ws + 0.1 + j * 0.16) * sr)
        buf[s:s + n] += (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 8) * 0.4)[: len(buf) - s]
    buf = np.clip(buf, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((buf * 32000).astype(np.int16).tobytes())


def draw_lane(d, sim, fr, i, y0, th, name, color, t, evs, times, rng_y, ball_end):
    layers, hp = sim["layers"], fr["hp"][i]
    fit_text(d, (W // 2, y0 + 30), name, 56, color, 900)
    box = (80, y0 + 70, 1000, y0 + 400)
    d.rectangle(box, fill=th["arena"], outline=th["ink"], width=4)
    x, y = ball_xy(t, evs, times, box, rng_y, 26)
    # damage popup after each hit
    k = bisect.bisect_right(times, t) - 1
    if k >= 0 and t - times[k] < 0.45:
        ex, ey = ball_xy(times[k], evs, times, box, rng_y, 26)
        a = 1 - (t - times[k]) / 0.45
        c = tuple(int(th["arena"][j] * (1 - a) + color[j] * a) for j in range(3))
        fit_text(d, (min(max(ex, 220), 860), min(ey + 50, box[3] - 20)), "-" + fmt(evs[k][2]), 30, c, 300)
    d.ellipse((x - 26, y - 26, x + 26, y + 26), fill=color, outline=th["ink"], width=3)
    fit_text(d, (box[0] + 16, box[1] + 14), f"DAMAGE: {fmt(fr['dmg'][i])}", 26, color, 600, anchor="lm")
    ry = box[3]
    for k2 in range(3):
        row = (80, ry + k2 * 62, 1000, ry + (k2 + 1) * 62)
        frac = hp[k2] / layers[k2]
        d.rectangle(row, fill=tuple(int(c * 0.35 + th["arena"][j] * 0.65) for j, c in enumerate(color)), outline=th["ink"], width=3)
        if hp[k2] > 0:
            d.rectangle((row[0], row[1], row[0] + (row[2] - row[0]) * frac, row[3]), fill=color)
            fit_text(d, ((row[0] + row[2]) // 2, (row[1] + row[3]) // 2), fmt(hp[k2]), 36, (255, 255, 255), 860)
        else:
            fit_text(d, ((row[0] + row[2]) // 2, (row[1] + row[3]) // 2), "BROKEN", 32, th["ghost"], 860)
    for cx in range(80, 1000, 24):  # finish strip
        for cy in range(2):
            c = th["ink"] if (cx // 24 + cy) % 2 == 0 else th["arena"]
            d.rectangle((cx, ry + 186 + cy * 12, cx + 24, ry + 198 + cy * 12), fill=c)


def render(sim, out_mp4, style="cream", header="", footer="Who wins? Comment your pick before the end.", handle="@ballsfighttoday"):
    th = THEMES[style]
    a, b = sim["names"]
    na, nb = engine.BALLS[a][0], engine.BALLS[b][0]
    evs = [lane_events(sim["events"], 0), lane_events(sim["events"], 1)]
    times = [[e[0] for e in evs[0]], [e[0] for e in evs[1]]]
    rng = random.Random(f"{a}{b}{sim['mode']}")
    rng_y = [[rng.random() for _ in range(max(len(evs[0]), len(evs[1])) + 4)] for _ in range(2)]
    end_hold = 3.0
    total = sim["duration"] + end_hold
    wav = out_mp4 + ".wav"
    make_audio(sim, wav, total)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
           "-shortest", "-movflags", "+faststart", out_mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(total * FPS)
    frames = sim["frames"]
    colors = (th["a"], th["b"])
    for f in range(nframes):
        t = f / FPS
        fr = frames[min(f, len(frames) - 1)]
        im = Image.new("RGB", (W, H), th["bg"])
        d = ImageDraw.Draw(im)
        fit_text(d, (W // 2, 90), header or f"{na} VS {nb}", 62, th["ink"], 960)
        fit_text(d, (W // 2, 150), engine.MODE_TEXT[sim["mode"]], 34, th["ghost"], 960)
        draw_lane(d, sim, fr, 0, 200, th, na, colors[0], t, evs[0], times[0], rng_y[0], None)
        d.text((W // 2, 868), "VS", font=font(54), fill=th["ink"], anchor="mm")
        draw_lane(d, sim, fr, 1, 900, th, nb, colors[1], t, evs[1], times[1], rng_y[1], None)
        fit_text(d, (W // 2, 1620), footer, 44, th["ink"], 960)
        fit_text(d, (W // 2, 1690), f"Bounces: {fr['n'][0]} vs {fr['n'][1]}", 34, th["ghost"], 960)
        fit_text(d, (W // 2, 1840), f"Follow {handle} for a new race every day", 36, th["ghost"], 960)
        if t >= sim["duration"] and sim["winner"] is not None:
            w = sim["winner"]
            d.rectangle((60, 760, 1020, 1060), fill=th["arena"], outline=th["ink"], width=6)
            fit_text(d, (W // 2, 860), (na, nb)[w] + " WINS", 78, colors[w], 900)
            fit_text(d, (W // 2, 960), "Comment the next matchup", 44, th["ink"], 900)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    p.wait()
    os.remove(wav)
    if p.returncode:
        raise SystemExit(f"::error::ffmpeg failed with code {p.returncode}")
