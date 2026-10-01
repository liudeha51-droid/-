#!/usr/bin/env python3
"""Render "HOLLOW FAITH — EPISODE:00", a 60-second EVA-style teaser.

Everything is procedural: frames are drawn with Pillow, the soundtrack is
synthesized with numpy, and ffmpeg muxes them into an H.264/AAC MP4.

    pip install pillow numpy
    python3 film/render_eva_short.py            # -> film/hollow_faith_ep00.mp4
"""
import math
import os
import random
import subprocess
import wave
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
FPS = 24
DUR = 60
N_FRAMES = FPS * DUR
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MP4 = os.path.join(HERE, "hollow_faith_ep00.mp4")
OUT_SHEET = os.path.join(HERE, "contact_sheet.png")

FONTS = {
    "serif": "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    "cjk": "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
}

WHITE = (255, 255, 255)
ORANGE = (255, 112, 0)
VERMILION = (235, 48, 28)
DIM_ORANGE = (90, 36, 0)
GREEN = (60, 255, 140)


# ----------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, x):
    return a + (b - a) * x


def ss(e0, e1, x):
    x = clamp((x - e0) / (e1 - e0))
    return x * x * (3 - 2 * x)


@lru_cache(None)
def font(kind, size):
    return ImageFont.truetype(FONTS[kind], size)


@lru_cache(None)
def text(s, kind, size, color=WHITE, sx=1.0, sy=1.0):
    """Render a string to a tight RGBA sprite, optionally squashed/stretched
    (EVA title cards rely on horizontally compressed, vertically tall type)."""
    f = font(kind, size)
    l, t, r, b = f.getbbox(s)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, 2 - t), s, font=f, fill=color + (255,))
    if sx != 1.0 or sy != 1.0:
        im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.LANCZOS)
    return im


def paste(base, sprite, x, y, anchor="lt", alpha=1.0):
    w, h = sprite.size
    if anchor[0] == "m":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    mask = sprite.getchannel("A")
    if alpha < 1.0:
        mask = mask.point(lambda v: int(v * clamp(alpha)))
    base.paste(sprite, (int(x), int(y)), mask)


def add_glow(base, layer, radius=16, strength=1.4):
    """Additively composite `layer` plus a cheap bloom (blurred at 1/4 res)."""
    small = layer.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(radius / 4))
    glow = np.asarray(small.resize((W, H), Image.BILINEAR), np.float32)
    out = np.asarray(base, np.float32) + np.asarray(layer, np.float32) + glow * strength
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def vgradient(stops):
    """Vertical gradient from [(y_frac, (r,g,b)), ...]."""
    ys = np.linspace(0, 1, H)
    cols = np.stack([np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], -1)
    return Image.fromarray(np.repeat(cols[:, None, :], W, 1).astype(np.uint8))


def black():
    return Image.new("RGB", (W, H), (0, 0, 0))


def hex_pts(cx, cy, r, rot=0.0):
    return [(cx + r * math.cos(math.pi / 3 * i + rot), cy + r * math.sin(math.pi / 3 * i + rot)) for i in range(6)]


def typed(s, t, cps=40):
    return s[: max(0, int(t * cps))]


# ---------------------------------------------------------- shared assets
SKY_RED = vgradient([(0, (40, 0, 4)), (0.45, (150, 18, 10)), (0.66, (255, 120, 40)), (0.67, (10, 4, 4)), (1, (0, 0, 0))])
SKY_DUSK = vgradient([(0, (18, 8, 40)), (0.4, (110, 30, 70)), (0.72, (255, 130, 50)), (1, (255, 190, 90))])
SKY_AFTER = vgradient([(0, (20, 0, 0)), (0.5, (90, 10, 6)), (0.68, (170, 40, 10)), (0.69, (8, 2, 2)), (1, (0, 0, 0))])


def make_city(seed, horizon, color):
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = -20
    while x < W:
        w = rnd.randint(18, 70)
        h = rnd.randint(20, 150)
        d.rectangle([x, horizon - h, x + w, H], fill=color + (255,))
        if rnd.random() < 0.3:
            d.rectangle([x + w // 2 - 2, horizon - h - rnd.randint(10, 40), x + w // 2 + 2, horizon - h], fill=color + (255,))
        x += w + rnd.randint(-6, 4)
    return layer


CITY_A = make_city(7, 482, (12, 4, 4))
CITY_B = make_city(11, 500, (0, 0, 0))

rng = np.random.default_rng(3)
GRAIN = [rng.normal(0, 4.5, (H, W, 1)).astype(np.float32) for _ in range(6)]
_yy, _xx = np.mgrid[0:H, 0:W]
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.clip(1.15 - 0.45 * _r ** 2, 0.35, 1.0).astype(np.float32)[..., None]
SCANLINES = (1 - 0.18 * (_yy % 3 == 0)).astype(np.float32)[..., None]


def subtitle(img, jp, en, alpha=1.0):
    paste(img, text(jp, "cjk", 38), W / 2, H - 92, "mb", alpha)
    paste(img, text(en, "mono", 18, (210, 210, 210)), W / 2, H - 52, "mb", alpha)


# ------------------------------------------------------------------ scenes
def sc_cold_open(t):
    img = black()
    d = ImageDraw.Draw(img)
    w = 520 * ss(0.4, 1.6, t)
    a = ss(0.4, 1.0, t) * (1 - ss(3.5, 3.95, t))
    if w > 1:
        d.line([(W / 2 - w, H / 2), (W / 2 + w, H / 2)], fill=tuple(int(255 * a) for _ in range(3)), width=1)
    if t > 1.3:
        flick = 1.0 if t > 1.6 or int(t * 30) % 2 else 0.2
        paste(img, text("東方虚信録", "cjk", 54), W / 2, H / 2 - 18, "mb", a * flick)
    line = typed("GREAT BARRIER DEFENSE BUREAU  //  INCIDENT RECORD 00", t - 1.8, 30)
    paste(img, text(line or " ", "mono", 18, ORANGE), W / 2 - 290, H / 2 + 22, "lt", a)
    return img


def sc_title(t):
    img = black()
    beats = [0.0, 0.55, 1.15, 1.8, 2.6]
    if t < 0.1 or 0.5 < t < 0.55:
        return img
    if t > beats[0]:
        paste(img, text("EPISODE:00", "serif", 40), 96, 70)
    if t > beats[1]:
        paste(img, text("虚ろなる", "cjk", 168, sx=0.82, sy=1.12), 82, 128)
    if t > beats[2]:
        paste(img, text("信仰", "cjk", 250, sx=0.9, sy=1.05), 600, 300)
    if t > beats[3]:
        paste(img, text("HOLLOW", "serif", 120, sx=0.6, sy=1.35), 96, 420)
        paste(img, text("FAITH", "serif", 120, sx=0.6, sy=1.35), 96, 560)
    if t > beats[4]:
        d = ImageDraw.Draw(img)
        d.line([(96, 404), (520, 404)], fill=WHITE, width=3)
    return img


def octahedron(img, cx, cy, scale, ang, tilt, eye):
    verts = [(1, 0, 0), (-1, 0, 0), (0, 1.5, 0), (0, -1.5, 0), (0, 0, 1), (0, 0, -1)]
    faces = [(2, 0, 4), (2, 4, 1), (2, 1, 5), (2, 5, 0), (3, 4, 0), (3, 1, 4), (3, 5, 1), (3, 0, 5)]
    ca, sa, ct, st = math.cos(ang), math.sin(ang), math.cos(tilt), math.sin(tilt)
    pv = []
    for x, y, z in verts:
        x, z = x * ca + z * sa, -x * sa + z * ca
        y, z = y * ct - z * st, y * st + z * ct
        k = 4 / (4 + z)
        pv.append((cx + x * scale * k, cy - y * scale * k, z))
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    d = ImageDraw.Draw(img)
    # halo ring behind
    rx, ry = scale * 1.9, scale * 0.42
    gd.ellipse([cx - rx, cy - scale * 1.6 - ry, cx + rx, cy - scale * 1.6 + ry], outline=(200, 40, 20), width=max(2, int(scale / 40)))
    order = sorted(faces, key=lambda f: -sum(pv[i][2] for i in f))
    for f in order:
        a, b, c = (np.array(pv[i][:2]) for i in f)
        cross = (b - a)[0] * (c - a)[1] - (b - a)[1] * (c - a)[0]
        if cross >= 0:
            continue
        zc = sum(pv[i][2] for i in f) / 3
        shade = int(clamp(0.5 - zc * 0.4) * 40)
        poly = [pv[i][:2] for i in f]
        d.polygon(poly, fill=(shade + 8, 2, 4))
        gd.line(poly + [poly[0]], fill=(255, 70, 30), width=2)
    if eye > 0:
        e = scale * 0.5 * eye
        gd.polygon([(cx, cy - e), (cx + e * 0.12, cy), (cx, cy + e), (cx - e * 0.12, cy)], fill=(255, 230, 200))
    return add_glow(img, glow, 22, 1.6)


def sc_approach(t):
    shake = 3 * ss(4, 6, t)
    ox, oy = random.uniform(-shake, shake), random.uniform(-shake, shake)
    img = SKY_RED.copy()
    scale = lerp(26, 150, ss(0, 6.5, t))
    img = octahedron(img, W / 2 + ox, lerp(300, 270, t / 7) + oy, scale, t * 0.7, 0.25, ss(5.2, 5.8, t))
    img.paste(CITY_A, (int(ox * 0.5), int(oy * 0.5)), CITY_A)
    img.paste(CITY_B, (int(ox), int(oy)), CITY_B)
    if t < 3.5:
        paste(img, text("TARGET: 7TH HOLLOW  —  ETA 00:04:12", "mono", 20, ORANGE), 40, 34)
    if 1.0 < t < 6.6:
        subtitle(img, "目標、第三防衛線を突破。", "TARGET HAS BREACHED THE THIRD DEFENSE LINE.", ss(1.0, 1.3, t))
    return img


def sc_alert(t):
    img = black()
    d = ImageDraw.Draw(img)
    for x in range(0, W, 40):
        d.line([(x, 0), (x, H)], fill=(22, 8, 0))
    for y in range(0, H, 40):
        d.line([(0, y), (W, y)], fill=(22, 8, 0))
    # hazard banner
    d.rectangle([0, 0, W, 86], fill=(0, 0, 0))
    for x in range(-100, W + 100, 46):
        off = (t * 120) % 46
        d.polygon([(x + off, 86), (x + 22 + off, 86), (x + 52 + off, 0), (x + 30 + off, 0)], fill=(120, 20, 0))
    paste(img, text("警報", "cjk", 64, VERMILION), 40, 43, "lm")
    paste(img, text("EMERGENCY  —  PATTERN: VERMILION", "serif", 44, WHITE, sx=0.78), 200, 43, "lm")
    # hex grid
    r = 44
    cx0, cy0 = 120, 150
    lit_radius = (t - 0.3) * 260
    blink = int(t * 4) % 2 == 0
    centre = (430, 400)
    for col in range(9):
        for row in range(6):
            hx = cx0 + col * 1.5 * r
            hy = cy0 + row * math.sqrt(3) * r + (col % 2) * math.sqrt(3) * r / 2
            dist = math.hypot(hx - centre[0], hy - centre[1])
            pts = hex_pts(hx, hy, r - 3)
            if dist < lit_radius and (blink or dist < lit_radius - 400):
                d.polygon(pts, fill=ORANGE)
                paste(img, text("EMERGENCY", "mono", 12, (0, 0, 0)), hx, hy, "mm")
            else:
                d.polygon(pts, outline=DIM_ORANGE)
                if dist < lit_radius:
                    paste(img, text("EMERGENCY", "mono", 12, DIM_ORANGE), hx, hy, "mm")
    # readout panel
    d.rectangle([880, 120, 1240, 680], outline=ORANGE, width=2)
    lines = [
        "> PATTERN ANALYSIS ........ VERMILION",
        "> CLASS ................... HOLLOW",
        "> DESIGNATION ............. 7TH",
        "> BARRIER INTEGRITY ....... 12.4%",
        "> SHRINE GRID ............. OFFLINE",
        "> FAITH RESERVE ........... CRITICAL",
        "> UNIT-00 'GOHEI' ......... STANDBY",
        "> PILOT ................... R.HAKUREI",
        "",
        "> 第一種戦闘配置",
        "> LEVEL 1 BATTLE STATIONS",
    ]
    y = 140
    for i, ln in enumerate(lines):
        s = typed(ln, t - 0.4 - i * 0.55, 60)
        if s:
            kind = "cjk" if any(ord(c) > 0x3000 for c in s) else "mono"
            col = VERMILION if "CRITICAL" in s or "12.4" in s or "第一" in s or "LEVEL" in s else ORANGE
            paste(img, text(s, kind, 15 if kind == "mono" else 22, col), 896, y)
        y += 44
    if blink and t > 4:
        flash = Image.new("RGB", (W, H), (120, 0, 0))
        img = Image.blend(img, flash, 0.18)
    return img


def sc_sync(t):
    img = black()
    d = ImageDraw.Draw(img)
    gx0, gy0, gx1, gy1 = 60, 150, 840, 600
    for x in range(gx0, gx1 + 1, 39):
        d.line([(x, gy0), (x, gy1)], fill=(0, 50, 22))
    for y in range(gy0, gy1 + 1, 45):
        d.line([(gx0, y), (gx1, y)], fill=(0, 50, 22))
    d.rectangle([gx0, gy0, gx1, gy1], outline=(0, 140, 60), width=2)
    conv = ss(0.5, 7.0, t)
    mid = (gy0 + gy1) / 2
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    for k, (col, f, ph) in enumerate([(ORANGE, 3.0, 0.0), (VERMILION, 4.7, 1.9), (GREEN, 2.2, 3.7)]):
        pts = []
        for i in range(0, gx1 - gx0, 4):
            u = i / (gx1 - gx0)
            freq = lerp(f, 3.0, conv)
            phase = lerp(ph, 0.0, conv) - t * 5
            amp = 140 * (1 - 0.5 * conv) * (1 + 0.25 * math.sin(t * 3 + k))
            pts.append((gx0 + i, mid + amp * math.sin(2 * math.pi * freq * u + phase)))
        gd.line(pts, fill=col, width=2)
    img = add_glow(img, glow, 10, 1.2)
    v = 99.89 * ss(0.3, 7.0, t)
    if t < 7.0:
        v += random.uniform(-0.6, 0.6) * (1 - conv)
    v = clamp(v, 0, 99.89 if t < 7.0 else 100.0)
    paste(img, text("シンクロ率", "cjk", 40, GREEN), 880, 160)
    paste(img, text("SYNCHRONIZATION RATIO", "mono", 18, (0, 170, 80)), 880, 214)
    paste(img, text(f"{v:05.2f}", "mono", 110, ORANGE, sx=0.8), 880, 250)
    paste(img, text("%", "mono", 50, ORANGE), 1180, 300)
    d = ImageDraw.Draw(img)
    for i in range(12):
        lvl = clamp(v / 100 * 12 - i)
        col = ORANGE if i < 9 else VERMILION
        d.rectangle([880 + i * 28, 420, 900 + i * 28, 470], outline=col, fill=col if lvl > 0.5 else None)
    paste(img, text("UNIT-00  //  NERVE LINK", "mono", 22, ORANGE), 60, 100)
    if t > 7.0 and int(t * 8) % 2 == 0:
        d.rectangle([880, 510, 1240, 580], fill=GREEN)
        paste(img, text("SYNCHRO: COMPLETE", "mono", 26, (0, 0, 0)), 1060, 545, "mm")
    if 2.0 < t < 6.0:
        subtitle(img, "思考形態は、霊夢の言語で固定。", "THOUGHT PATTERN LOCKED TO PILOT LANGUAGE.", ss(2.0, 2.3, t))
    return img


CARDS = [
    ("起動", "ACTIVATE", "bw"),
    ("拒絶", "REJECTION", "wb"),
    ("祈り", "PRAYER", "bw"),
    ("結界", "BARRIER", "red"),
    ("虚無", "HOLLOW", "bw"),
    ("信仰", "FAITH", "wb"),
    ("あなたは、何を信じるの？", "WHAT DO YOU BELIEVE IN?", "bw"),
    ("発進", "LAUNCH", "red"),
]
CARD_LEN = 0.75


def sc_cards(t):
    i = min(int(t / CARD_LEN), len(CARDS) - 1)
    lt = t - i * CARD_LEN
    jp, en, style = CARDS[i]
    bg, fg = {"bw": ((0, 0, 0), WHITE), "wb": (WHITE, (0, 0, 0)), "red": ((170, 0, 0), WHITE)}[style]
    if lt < 1 / FPS * 1.5 and i % 2:
        return Image.new("RGB", (W, H), WHITE)
    img = Image.new("RGB", (W, H), bg)
    size = 90 if len(jp) > 4 else 300
    s = text(jp, "cjk", size, fg, sx=0.88, sy=1.1)
    paste(img, s, W / 2 + (i % 3 - 1) * 60, H / 2 - 30, "mm")
    paste(img, text(en, "serif", 46, fg, sx=0.75), W / 2 + (i % 3 - 1) * 60, H / 2 + s.height / 2 + 10, "mt")
    return img


def sc_launch(t):
    img = Image.new("RGB", (W, H), (6, 4, 8))
    d = ImageDraw.Draw(img)
    speed = lerp(600, 4200, ss(0, 3.6, t))
    pos = 600 * t + 3600 * max(0, t - 0.5) ** 2 / 2
    rnd = random.Random(5)
    shake = 2 + 6 * ss(1, 3.6, t)
    ox = random.uniform(-shake, shake)
    for _ in range(90):
        x = rnd.uniform(0, W)
        ln = rnd.uniform(40, 220) * speed / 1500
        y = (rnd.uniform(0, H * 3) + pos * rnd.uniform(0.8, 1.4)) % (H + ln) - ln
        c = rnd.randint(40, 120)
        d.line([(x + ox, y), (x + ox, y + ln)], fill=(c, c // 2, c // 3), width=1)
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    gap = 420
    off = pos % gap
    for k in range(-1, H // gap + 2):
        y = k * gap + off
        gd.rectangle([0, y, W, y + 6], fill=(255, 150, 60))
    # shaft walls
    d.rectangle([0, 0, 140 + ox, H], fill=(14, 10, 12))
    d.rectangle([W - 140 + ox, 0, W, H], fill=(14, 10, 12))
    img = add_glow(img, glow, 18, 1.0)
    paste(img, text("UNIT-00  LIFT OFF", "mono", 28, ORANGE), 180, 40)
    paste(img, text(f"ALT {int(pos * 0.9):06d} m", "mono", 22, ORANGE), 180, 80)
    if t > 0.4:
        subtitle(img, "御幣零号機、発進！", "UNIT-00 'GOHEI', LAUNCH!", ss(0.4, 0.6, t))
    return img


MECH_PARTS = [
    [(-3, 20), (-34, 2), (-28, 32)],  # bow, left
    [(3, 20), (34, 2), (28, 32)],  # bow, right
    [(-4, 15), (-2, 15), (-13, -2)],  # horn, left
    [(4, 15), (2, 15), (13, -2)],  # horn, right
    [(-6, 14), (6, 14), (8, 24), (4, 32), (-4, 32), (-8, 24)],  # head
    [(-3, 30), (3, 30), (3, 39), (-3, 39)],  # neck
    [(-20, 38), (20, 38), (16, 80), (8, 96), (-8, 96), (-16, 80)],  # torso
    [(-36, 33), (-17, 36), (-17, 57), (-38, 61)],  # pylon, left
    [(36, 33), (17, 36), (17, 57), (38, 61)],  # pylon, right
    [(-34, 58), (-24, 58), (-26, 112), (-35, 112)],  # arm, left
    [(24, 58), (34, 58), (39, 108), (30, 111)],  # arm, right
    [(-10, 95), (10, 95), (13, 109), (-13, 109)],  # waist
    [(-14, 106), (-2, 106), (-4, 210), (-19, 210)],  # leg, left
    [(14, 106), (2, 106), (4, 210), (19, 210)],  # leg, right
]


def sc_mech(t):
    img = SKY_DUSK.copy()
    d = ImageDraw.Draw(img)
    d.ellipse([W / 2 - 180, 420, W / 2 + 180, 780], fill=(255, 220, 150))
    s = 3.3
    ox = W / 2
    oy = lerp(150, 40, ss(0, 5.5, t))
    tf = lambda p: (ox + p[0] * s, oy + p[1] * s)
    # orange rim light: silhouette drawn offset, then black on top
    for dx, dy in [(-3, -2), (3, -2)]:
        for part in MECH_PARTS:
            d.polygon([(x + dx, y + dy) for x, y in map(tf, part)], fill=(255, 120, 40))
    for part in MECH_PARTS:
        d.polygon([tf(p) for p in part], fill=(4, 2, 6))
    # gohei staff with zig-zag shide
    d.line([tf((32, 150)), tf((50, -10))], fill=(4, 2, 6), width=9)
    for side in (-1, 1):
        zz = [tf((50, -10))]
        for k in range(1, 6):
            zz.append(tf((50 + side * (4 if k % 2 else 9), -10 + k * 7)))
        d.line(zz, fill=(235, 235, 230), width=6, joint="curve")
    img.paste(CITY_B, (0, 120), CITY_B)
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    eye = ss(1.6, 2.0, t) * (0.8 + 0.2 * math.sin(t * 20))
    if eye > 0:
        for ex in (-3.2, 3.2):
            x, y = tf((ex, 23))
            r = 9 * eye
            gd.ellipse([x - r * 1.6, y - r * 0.6, x + r * 1.6, y + r * 0.6], fill=(int(255 * eye), int(240 * eye), int(120 * eye)))
    img = add_glow(img, glow, 26, 3.0)
    if 2.4 < t < 5.6:
        subtitle(img, "……行きます。", "…I'M GOING.", ss(2.4, 2.7, t) * (1 - ss(5.3, 5.6, t)))
    return img


SHARDS = [(random.Random(i).uniform(0, 2 * math.pi), random.Random(i + 99).uniform(150, 650), random.Random(i + 7).uniform(8, 28)) for i in range(48)]


def sc_impact(t):
    if t < 3 / FPS:
        return Image.new("RGB", (W, H), WHITE)
    img = SKY_AFTER.copy()
    img.paste(CITY_A, (0, 20), CITY_A)
    cx, cy = W / 2, 470
    grow = ss(0.08, 0.5, t)
    fade = math.exp(-max(0, t - 0.4) / 1.8)
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    vw = (30 + 50 * grow) * (0.4 + 0.6 * fade)
    col = (int(255 * fade), int(210 * fade), int(170 * fade))
    gd.rectangle([cx - vw / 2, -20, cx + vw / 2, cy + 40], fill=col)
    hw = W * 0.34 * grow
    gd.rectangle([cx - hw, 250 - vw / 2.4, cx + hw, 250 + vw / 2.4], fill=col)
    # barrier field: expanding hexagons
    for k in range(5):
        rr = (t - 1.3) * 340 - k * 90
        if rr > 10:
            a = clamp(1 - rr / 900)
            gd.polygon(hex_pts(cx, cy - 120, rr, math.pi / 6), outline=(int(255 * a), int(120 * a), 0), width=3)
    img = add_glow(img, glow, 30, 2.2)
    d = ImageDraw.Draw(img)
    for ang, sp, sz in SHARDS:
        dist = sp * (t - 0.1) if t > 0.1 else 0
        x, y = cx + math.cos(ang) * dist, 250 + math.sin(ang) * dist * 0.7 + 60 * t * t
        a = ang + t * 3
        d.polygon([(x + sz * math.cos(a + k * 2.1), y + sz * math.sin(a + k * 2.1)) for k in range(3)], fill=(10, 2, 2))
    if 2.4 < t < 6.6:
        subtitle(img, "結界、全開。", "BARRIER FIELD — FULL DEPLOYMENT.", ss(2.4, 2.7, t) * (1 - ss(6.3, 6.6, t)))
    return img


def sc_next(t):
    img = black()
    fade = 1 - ss(4.2, 4.9, t)
    if t > 0.3:
        paste(img, text("次回予告", "cjk", 34), 96, 80, alpha=fade)
        paste(img, text("NEXT EPISODE", "serif", 30, sx=0.8), 96, 124, alpha=fade)
    if t > 1.0:
        paste(img, text("第弐話", "cjk", 150, sx=0.85, sy=1.1), 96, 190, alpha=fade)
    if t > 1.7:
        paste(img, text("祈りは、届かない", "cjk", 110, sx=0.8, sy=1.15), W - 96, 400, "rt", fade)
    if t > 2.6:
        paste(img, text("THE PRAYER DOES NOT REACH", "serif", 40, sx=0.72), W - 96, 560, "rt", fade)
    return img


TIMELINE = [
    (0.0, 4.0, sc_cold_open),
    (4.0, 9.0, sc_title),
    (9.0, 16.0, sc_approach),
    (16.0, 24.0, sc_alert),
    (24.0, 32.0, sc_sync),
    (32.0, 38.0, sc_cards),
    (38.0, 42.0, sc_launch),
    (42.0, 48.0, sc_mech),
    (48.0, 55.0, sc_impact),
    (55.0, 60.0, sc_next),
]
GLITCH = [(15.1, 15.4), (23.8, 24.1), (41.6, 42.05), (48.0, 48.6)]
SCANLINE_SCENES = (sc_alert, sc_sync, sc_launch)


def render_frame(i):
    t = i / FPS
    for t0, t1, fn in TIMELINE:
        if t0 <= t < t1:
            img = fn(t - t0)
            break
    arr = np.asarray(img, np.float32)
    if fn in SCANLINE_SCENES:
        arr = arr * SCANLINES
    if any(a <= t < b for a, b in GLITCH):
        sh = random.randint(6, 18)
        arr[..., 0] = np.roll(arr[..., 0], sh, 1)
        arr[..., 2] = np.roll(arr[..., 2], -sh, 1)
        y0 = random.randint(0, H - 60)
        arr[y0:y0 + 40] = np.roll(arr[y0:y0 + 40], random.randint(-80, 80), 1)
    arr = arr * VIGNETTE + GRAIN[i % len(GRAIN)]
    return np.clip(arr, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------- audio
SR = 44100


def synth_audio(path):
    n = SR * DUR
    tt = np.arange(n) / SR
    out = np.zeros(n)
    nrng = np.random.default_rng(1)

    def place(sig, start):
        s = int(start * SR)
        e = min(n, s + len(sig))
        if s < n:
            out[s:e] += sig[: e - s]

    def seg(dur):
        return np.arange(int(dur * SR)) / SR

    def lowpass(x, k):
        return np.convolve(x, np.ones(k) / k, "same")

    def thump(f, amp):
        u = seg(0.35)
        return amp * np.sin(2 * np.pi * f * u * (1 - 0.6 * u)) * np.exp(-u * 14)

    def heartbeat(t0):
        place(thump(62, 0.9), t0)
        place(thump(52, 0.6), t0 + 0.2)

    def hit(t0, amp=0.6):
        u = seg(0.6)
        place(amp * (np.sin(2 * np.pi * 70 * u * (1 - 0.4 * u)) * np.exp(-u * 7)
                     + 0.5 * nrng.normal(0, 1, len(u)) * np.exp(-u * 40)), t0)

    # low drone with section-dependent level
    drone = (0.5 * np.sin(2 * np.pi * 41.2 * tt) + 0.3 * np.sin(2 * np.pi * 55 * tt + 0.6 * np.sin(2 * np.pi * 0.11 * tt))
             + 0.2 * np.sin(2 * np.pi * 82.4 * tt) + 0.25 * lowpass(nrng.normal(0, 1, n), 60))
    lvl = np.interp(tt, [0, 4, 9, 15.8, 16, 24, 32, 38, 42, 48, 50, 55, 56, 60],
                    [0.05, 0.08, 0.15, 0.5, 0.2, 0.25, 0.1, 0.25, 0.5, 0.35, 0.4, 0.3, 0.0, 0.0])
    out += drone * lvl

    for b in (0.4, 1.4, 2.4, 3.4):
        heartbeat(b)
    b, gap = 24.2, 0.9
    while b < 31.6:
        heartbeat(b)
        b += gap
        gap = max(0.33, gap * 0.9)

    # title-card and cut stingers
    for s in (4.0, 4.55, 5.15, 5.8, 6.6, 9.0, 16.0, 24.0, 55.3, 56.0, 56.7):
        hit(s, 0.5)
    for k in range(len(CARDS)):
        hit(32.0 + k * CARD_LEN, 0.75)
    hit(42.0, 0.9)

    # two-tone klaxon
    k = 0
    while 16.3 + k * 0.32 < 23.9:
        u = seg(0.3)
        f = 880 if k % 2 else 660
        env = np.minimum(1, u * 60) * np.minimum(1, (0.3 - u) * 60)
        place(0.12 * np.tanh(3 * np.sin(2 * np.pi * f * u)) * env, 16.3 + k * 0.32)
        k += 1
    for c in np.sort(nrng.uniform(16.4, 23.5, 70)):  # readout typing ticks
        place(0.12 * nrng.normal(0, 1, 120) * np.exp(-np.arange(120) / 25), c)

    # sync rising tone
    u = seg(8)
    f = np.interp(u, [0, 7, 8], [180, 820, 820])
    place(0.08 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, u / 0.5) * np.minimum(1, (8 - u) * 4), 24.0)

    # launch: rising sweep + roar
    u = seg(4)
    f = 90 + 1100 * (u / 4) ** 2
    roar = lowpass(nrng.normal(0, 1, len(u)), 12) * (u / 4) ** 1.5
    place(0.18 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (u / 4) + 0.9 * roar, 38.0)

    # mech eyes: resonant hum
    u = seg(4.5)
    place(0.25 * np.sin(2 * np.pi * 110 * u) * np.sin(2 * np.pi * 0.5 * u) ** 2 * np.minimum(1, u * 2), 43.5)

    # impact
    u = seg(5)
    boom = lowpass(nrng.normal(0, 1, len(u)), 30) * np.exp(-u * 1.2) * 2.4
    boom += 0.9 * np.sin(2 * np.pi * np.cumsum(np.interp(u, [0, 2], [70, 28])) / SR) * np.exp(-u * 0.9)
    place(boom, 48.0)

    # outro pad + bell
    u = seg(4.8)
    pad = sum(np.sin(2 * np.pi * f * u) for f in (220.0, 261.63, 329.63, 440.0)) / 4
    place(0.18 * pad * np.minimum(1, u / 1.2) * np.minimum(1, (4.8 - u) / 1.0), 55.2)
    for bt, bf in ((55.3, 880), (56.0, 659.3), (56.7, 587.3), (57.6, 440)):
        u = seg(2)
        place(0.2 * (np.sin(2 * np.pi * bf * u) + 0.3 * np.sin(2 * np.pi * bf * 2.01 * u)) * np.exp(-u * 2.5), bt)

    out = np.tanh(out * 1.1)
    out = out / max(1e-9, np.abs(out).max()) * 0.9
    left = out
    right = np.concatenate([np.zeros(220), out[:-220]])
    pcm = (np.stack([left, right], 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# -------------------------------------------------------------------- main
def main():
    random.seed(42)
    wav = os.path.join(HERE, "_soundtrack.wav")
    synth_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", OUT_MP4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    sheet_times = [2.5, 7.5, 14.6, 20.5, 31.5, 34.5, 40.0, 46.0, 49.2, 58.0]
    thumbs = {}
    for i in range(N_FRAMES):
        frame = render_frame(i)
        proc.stdin.write(frame.tobytes())
        for st in sheet_times:
            if i == int(st * FPS):
                thumbs[st] = Image.fromarray(frame).resize((W // 4, H // 4), Image.LANCZOS)
        if i % (FPS * 5) == 0:
            print(f"  {i / FPS:4.0f}s / {DUR}s", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")
    os.remove(wav)
    sheet = Image.new("RGB", (W // 4 * 5 + 24, H // 4 * 2 + 12), (0, 0, 0))
    for k, st in enumerate(sheet_times):
        sheet.paste(thumbs[st], (4 + (k % 5) * (W // 4 + 4), 4 + (k // 5) * (H // 4 + 4)))
    sheet.save(OUT_SHEET)
    print("wrote", OUT_MP4, "and", OUT_SHEET)


if __name__ == "__main__":
    main()
