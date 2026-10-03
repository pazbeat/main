"""Procedural textures for the knight character (PIL only).

Run:  python3 make_textures.py   -> writes PNGs into ./textures
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageChops

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
os.makedirs(OUT, exist_ok=True)
random.seed(7)


def noise(size, scale, amp, base=128):
    """Cheap value noise: upscale random small image."""
    small = Image.new("L", (max(2, size // scale), max(2, size // scale)))
    small.putdata([int(base + random.uniform(-amp, amp)) for _ in range(small.size[0] * small.size[1])])
    return small.resize((size, size), Image.BICUBIC)


def tint(gray, color, strength=1.0):
    """Map grayscale (128 = neutral) onto a base color."""
    r, g, b = color
    lut = []
    for c in (r, g, b):
        lut += [max(0, min(255, int(c * (1 + strength * (i - 128) / 128.0)))) for i in range(256)]
    return Image.merge("RGB", (gray, gray, gray)).point(lut)


def multi_noise(size, octaves):
    acc = Image.new("L", (size, size), 128)
    for scale, amp in octaves:
        n = noise(size, scale, amp)
        acc = ImageChops.add(acc, n, scale=1.0, offset=-128)
    return acc


# ---------------------------------------------------------------- leather
def leather(name, color, size=512):
    g = multi_noise(size, [(64, 18), (16, 12), (4, 10), (1, 10)])
    d = ImageDraw.Draw(g)
    for _ in range(140):  # scratches / creases
        x, y = random.uniform(0, size), random.uniform(0, size)
        a = random.uniform(0, math.pi)
        l = random.uniform(6, 40)
        d.line([(x, y), (x + l * math.cos(a), y + l * math.sin(a))],
               fill=random.choice([90, 100, 170, 180]), width=1)
    g = g.filter(ImageFilter.GaussianBlur(0.6))
    tint(g, color, 0.9).save(os.path.join(OUT, name))


# ---------------------------------------------------------------- quilted gambeson
def gambeson(size=512):
    g = multi_noise(size, [(32, 16), (4, 10), (1, 12)])
    step = size // 12
    shade = Image.new("L", (size, size))
    sd = ImageDraw.Draw(shade)
    for yy in range(size):
        k = yy % step
        sd.line([(0, yy), (size, yy)], fill=int(100 + 60 * math.sin(math.pi * k / step)))
    g = ImageChops.multiply(g, shade.point(lambda v: min(255, v + 60)))
    d = ImageDraw.Draw(g)
    for i in range(13):
        d.line([(0, i * step), (size, i * step)], fill=40, width=2)
        for x in range(0, size, 6):  # stitches
            d.point((x, i * step + 1), fill=150)
    tint(g.filter(ImageFilter.GaussianBlur(0.5)), (96, 90, 62), 0.8).save(os.path.join(OUT, "gambeson.png"))


# ---------------------------------------------------------------- cloth (cloak / trousers)
def cloth(name, color, size=512):
    g = multi_noise(size, [(64, 22), (8, 10)])
    weave = Image.new("L", (size, size))
    wd = ImageDraw.Draw(weave)
    for y in range(size):
        for x in range(0, size, 2):
            if (x // 2 + y) % 2 == 0:
                wd.point((x, y), fill=150)
            else:
                wd.point((x, y), fill=110)
    g = ImageChops.add(g, weave, scale=1.0, offset=-128)
    tint(g.filter(ImageFilter.GaussianBlur(0.4)), color, 0.7).save(os.path.join(OUT, name))


# ---------------------------------------------------------------- chainmail
def chainmail(size=512):
    img = Image.new("L", (size, size), 35)
    d = ImageDraw.Draw(img)
    r = 7
    for row in range(-1, size // (r) + 2):
        off = (row % 2) * r
        for col in range(-1, size // (2 * r) + 2):
            cx, cy = col * 2 * r + off, row * r * 1.0
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=190, width=3)
            d.arc([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], 200, 300, fill=240, width=1)
    img = ImageChops.multiply(img, multi_noise(size, [(32, 40)]).point(lambda v: min(255, v + 70)))
    tint(img, (150, 150, 155), 1.0).save(os.path.join(OUT, "chainmail.png"))


# ---------------------------------------------------------------- brushed / worn steel
def steel(size=512):
    g = multi_noise(size, [(128, 20), (32, 10)])
    d = ImageDraw.Draw(g)
    for _ in range(600):
        y = random.uniform(0, size)
        x = random.uniform(0, size)
        d.line([(x, y), (x + random.uniform(10, 80), y + random.uniform(-1, 1))],
               fill=random.choice([105, 150, 160]), width=1)
    for _ in range(40):  # dents / grime spots
        x, y = random.uniform(0, size), random.uniform(0, size)
        s = random.uniform(2, 8)
        d.ellipse([x - s, y - s, x + s, y + s], fill=random.choice([80, 95]))
    tint(g.filter(ImageFilter.GaussianBlur(0.7)), (168, 170, 174), 0.6).save(os.path.join(OUT, "steel.png"))


# ---------------------------------------------------------------- shield face with eagle
def eagle_polys(cx, cy, s):
    """Heraldic eagle facing left (viewer's left), wings raised. Returns polygons."""
    P = lambda pts: [(cx + x * s, cy + y * s) for x, y in pts]
    polys = []
    # body (teardrop)
    polys.append(P([(-0.10, -0.30), (0.10, -0.32), (0.20, -0.10), (0.18, 0.15), (0.08, 0.32),
                    (-0.08, 0.32), (-0.16, 0.10), (-0.16, -0.12)]))
    # neck + head looking left
    polys.append(P([(-0.06, -0.30), (0.06, -0.32), (0.02, -0.46), (-0.08, -0.56), (-0.22, -0.58),
                    (-0.32, -0.54), (-0.40, -0.50), (-0.30, -0.47), (-0.20, -0.44), (-0.14, -0.38)]))
    # beak hook
    polys.append(P([(-0.38, -0.55), (-0.48, -0.50), (-0.44, -0.44), (-0.36, -0.47)]))
    # right wing (viewer's right) raised, feathered
    rw = [(0.12, -0.20), (0.30, -0.42), (0.50, -0.62), (0.70, -0.74), (0.86, -0.78)]
    tips = [(0.92, -0.62), (0.80, -0.56), (0.90, -0.40), (0.74, -0.36), (0.84, -0.18), (0.64, -0.16),
            (0.70, 0.02), (0.48, -0.02), (0.50, 0.14), (0.30, 0.06), (0.18, 0.12)]
    polys.append(P(rw + tips))
    # left wing (viewer's left)
    lw = [(-0.12, -0.18), (-0.28, -0.36), (-0.46, -0.52), (-0.66, -0.60), (-0.82, -0.62)]
    tips = [(-0.86, -0.48), (-0.74, -0.44), (-0.84, -0.28), (-0.68, -0.26), (-0.76, -0.08), (-0.56, -0.08),
            (-0.60, 0.08), (-0.40, 0.02), (-0.40, 0.16), (-0.22, 0.08), (-0.16, 0.12)]
    polys.append(P(lw + tips))
    # tail feathers
    polys.append(P([(-0.10, 0.28), (0.10, 0.28), (0.22, 0.60), (0.10, 0.52), (0.04, 0.66), (-0.04, 0.52),
                    (-0.12, 0.64), (-0.14, 0.50), (-0.26, 0.58)]))
    # legs + talons
    for sx in (-1, 1):
        polys.append(P([(sx * 0.06, 0.24), (sx * 0.14, 0.24), (sx * 0.24, 0.42), (sx * 0.30, 0.44),
                        (sx * 0.26, 0.48), (sx * 0.20, 0.46), (sx * 0.16, 0.52), (sx * 0.12, 0.44)]))
    return polys


def shield(size=1024):
    W, H = size, int(size * 1.4)
    g = Image.new("L", (W, H), 128)
    planks = 6
    pw = W / planks
    for i in range(planks):  # vertical planks with grain
        plank = multi_noise(max(W, H), [(64, 25), (4, 8)]).crop((0, 0, int(pw) + 2, H))
        # streaky grain
        streak = Image.new("L", plank.size, 128)
        sd = ImageDraw.Draw(streak)
        x = 0.0
        while x < plank.size[0]:
            wob = random.uniform(-3, 3)
            sd.line([(x, 0), (x + wob, H)], fill=random.choice([95, 110, 150, 165]), width=random.choice([1, 2]))
            x += random.uniform(2, 7)
        streak = streak.filter(ImageFilter.GaussianBlur(1.0))
        plank = ImageChops.add(plank, streak, scale=1.0, offset=-128)
        plank = plank.point(lambda v, k=random.uniform(-14, 14): int(max(0, min(255, v + k))))
        g.paste(plank, (int(i * pw), 0))
    d = ImageDraw.Draw(g)
    for i in range(1, planks):  # plank gaps
        d.line([(i * pw, 0), (i * pw, H)], fill=30, width=5)
    for _ in range(60):  # scratches / chips
        x, y = random.uniform(0, W), random.uniform(0, H)
        a = random.uniform(0, math.pi)
        l = random.uniform(10, 70)
        d.line([(x, y), (x + l * math.cos(a), y + l * math.sin(a))], fill=random.choice([200, 70]), width=2)
    wood = tint(g, (128, 78, 42), 0.8)
    # darker weathered edges (vignette)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle([60, 60, W - 60, H - 60], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(80))
    dark = tint(g, (70, 40, 20), 0.6)
    wood = Image.composite(wood, dark, vig)
    # eagle
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for poly in eagle_polys(W * 0.5, H * 0.43, W * 0.42):
        md.polygon(poly, fill=255)
    # distress the paint
    distress = multi_noise(max(W, H), [(4, 90), (1, 60)]).crop((0, 0, W, H)).point(lambda v: 0 if v < 38 else 255)
    mask = ImageChops.multiply(mask, distress).filter(ImageFilter.GaussianBlur(1.2))
    paint = Image.new("RGB", (W, H), (18, 16, 15))
    out = Image.composite(paint, wood, mask)
    out.save(os.path.join(OUT, "shield_face.png"))


# ---------------------------------------------------------------- skin
def skin(size=256):
    g = multi_noise(size, [(32, 8), (2, 6)])
    tint(g, (150, 104, 84), 0.5).save(os.path.join(OUT, "skin.png"))


if __name__ == "__main__":
    leather("leather_brown.png", (72, 41, 24))
    leather("leather_dark.png", (46, 27, 16))
    leather("leather_boot.png", (62, 40, 27))
    gambeson()
    cloth("cloak_green.png", (28, 50, 32))
    cloth("cloak_brown.png", (86, 54, 30))
    cloth("trousers.png", (34, 48, 34))
    chainmail()
    steel()
    shield()
    skin()
    print("textures written to", OUT)
