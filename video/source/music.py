import numpy as np, wave, subprocess

SR = 48000
DUR = 76.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
t_all = np.arange(N) / SR


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    na = min(na, n); nr = min(nr, n - na)
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr > 0:
        e[n - nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def chunk_feedback(x, D, g):
    """y[n] = x[n] + g*y[n-D]"""
    y = x.copy()
    for i in range(D, len(y), D):
        j = min(i + D, len(y))
        y[i:j] += g * y[i - D:j - D]
    return y


def allpass(x, D, g):
    # y[n] = -g x[n] + x[n-D] + g y[n-D]
    xd = np.zeros_like(x); xd[D:] = x[:-D]
    v = -g * x + xd
    return chunk_feedback(v, D, g)


def reverb(x, seed=0, mix=.35):
    combs = [1557, 1617, 1491, 1422, 1277, 1356]
    combs = [int(c * 1.9) + seed * 23 for c in combs]
    out = np.zeros_like(x)
    for c in combs:
        y = chunk_feedback(x, c, .84)
        out += y
    out /= len(combs)
    for d in [225 + seed * 7, 556 + seed * 11, 441]:
        out = allpass(out, int(d * 1.9), .6)
    # simple lowpass on the tail
    out = lowpass(out, 5500)
    return x * (1 - mix) + out * mix


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    # one pole via lfilter-like recursion using cumulative trick is hard; do small loop in blocks
    from itertools import accumulate
    y = np.empty_like(x)
    prev = 0.0
    b = 1 - a
    # vectorised with scipy absent: use python loop on float64 array (fast enough for 3.6M? ~2s)
    xs = x.tolist()
    ys = []
    ap = ys.append
    for v in xs:
        prev = b * v + a * prev
        ap(prev)
    return np.array(ys)


# ---------------- pad ----------------
# chords (midi), each 6.4 s
D = 6.4
prog = [
    [50, 57, 62, 66, 69, 76],   # Dmaj9-ish (D A D F# A E)
    [47, 54, 59, 62, 66, 73],   # Bm9 (B F# B D F# C#)
    [43, 50, 55, 59, 62, 69],   # Gmaj7 add9 (G D G B D A)
    [45, 52, 57, 62, 64, 71],   # Asus (A E A D E B)
]
pad = np.zeros((N, 2))
chords = []
tt = 0.0
k = 0
while tt < 69.0:
    chords.append((tt, prog[k % 4])); tt += D; k += 1
# final resolve
chords.append((tt, [38, 50, 57, 62, 66, 69, 74]))

for ci, (t0, notes) in enumerate(chords):
    last = ci == len(chords) - 1
    length = (DUR - t0) if last else D + 2.2
    n = int(length * SR); s = int(t0 * SR)
    n = min(n, N - s)
    tl = np.arange(n) / SR
    e = env_adsr(n, 1.8, 2.6 if not last else 4.5)
    for j, m in enumerate(notes):
        f = midi(m)
        vol = .09 if m < 48 else .055
        sig = np.zeros(n)
        for dt in (-0.12, 0, 0.13):
            ff = f * 2 ** (dt / 12 / 4)
            ph = rng.uniform(0, 6.28)
            sig += np.sin(2 * np.pi * ff * tl + ph) + .18 * np.sin(4 * np.pi * ff * tl + ph) + .06 * np.sin(6 * np.pi * ff * tl)
        trem = 1 + .12 * np.sin(2 * np.pi * (.13 + .03 * j) * tl + j)
        sig = sig / 3 * vol * trem * e
        pan = .5 + .35 * np.sin(j * 1.7)
        pad[s:s + n, 0] += sig * (1 - pan) * 1.4
        pad[s:s + n, 1] += sig * pan * 1.4

# ---------------- plucks (khim-like) ----------------
def pluck(f, dur, bright=.5):
    n = int(dur * SR)
    Np = int(SR / f)
    z = np.zeros(n + 1)
    burst = rng.uniform(-1, 1, Np)
    # soften burst
    for _ in range(int(3 - bright * 2)):
        burst = .5 * (burst + np.roll(burst, 1))
    z[1:Np + 1] = burst
    dec = .996
    for i in range(Np + 1, n + 1, Np):
        j = min(i + Np, n + 1)
        z[i:j] = dec * .5 * (z[i - Np:j - Np] + z[i - Np - 1:j - Np - 1])
    y = z[1:]
    # add a bit of sine body for bell-ish tone
    tl = np.arange(n) / SR
    y += .35 * np.sin(2 * np.pi * f * tl) * np.exp(-tl * 2.2)
    y *= np.exp(-tl * .9)
    return y

scale_by_chord = [
    [62, 64, 66, 69, 71, 74, 76, 78, 81],
    [59, 61, 62, 66, 69, 71, 73, 74, 78],
    [59, 62, 64, 66, 67, 69, 71, 74, 79],
    [57, 59, 61, 64, 66, 69, 71, 73, 76],
]
plk = np.zeros((N, 2))
beat = D / 8  # 0.8s -> 8th = .4
step = beat / 2
start_pl = 3.2
ti = start_pl
idx = 0
pattern = [0, 2, 4, 3, 5, 4, 2, 1, 3, 5, 6, 4, 2, 3, 1, 0]
while ti < DUR - 6.5:
    ci = int(ti // D) % 4
    sc = scale_by_chord[ci]
    # density: sparser in welcome section (voice), fuller after
    dens = .35 if 4.4 < ti < 13.2 else (.8 if 20 < ti < 60 else .6)
    if rng.random() < dens:
        m = sc[min(len(sc) - 1, pattern[idx % 16] + (2 if (idx // 16) % 2 else 0))]
        v = .05 + .04 * rng.random()
        y = pluck(midi(m), 3.0, .5) * v
        s = int((ti + rng.normal(0, .008)) * SR)
        n = min(len(y), N - s)
        pan = .5 + .3 * np.sin(idx * .9)
        plk[s:s + n, 0] += y[:n] * (1 - pan)
        plk[s:s + n, 1] += y[:n] * pan
    idx += 1
    ti += step

# ---------------- chimes at key moments ----------------
def chime(f0, dur=5.0):
    n = int(dur * SR); tl = np.arange(n) / SR
    y = np.zeros(n)
    for ratio, amp, d in [(1, 1, 1.4), (2.76, .5, 2.2), (5.4, .25, 3.5), (8.93, .12, 5)]:
        y += amp * np.sin(2 * np.pi * f0 * ratio * tl) * np.exp(-tl * d)
    y *= np.minimum(1, tl / .004)
    return y * .06

chm = np.zeros((N, 2))
for tc, m in [(0.35, 86), (2.25, 81), (70.6, 86), (71.0, 90)]:
    y = chime(midi(m)); s = int(tc * SR); n = min(len(y), N - s)
    chm[s:s + n, 0] += y[:n]; chm[s:s + n, 1] += y[:n] * .8

# soft whoosh (filtered noise swell) on scene changes
wh = np.zeros((N, 2))
for tc in [12.8, 20.1, 29.1, 38.1, 43.8, 57.1, 63.1, 68.7]:
    n = int(1.2 * SR); s = int((tc - .6) * SR)
    noise = rng.normal(0, 1, n)
    for _ in range(6):
        noise = .5 * (noise + np.roll(noise, 1))
    e = np.sin(np.linspace(0, np.pi, n)) ** 3
    y = noise * e * .012
    wh[s:s + n, 0] += y; wh[s:s + n, 1] += np.roll(y, 300)

dry = pad + plk + chm
wet = np.stack([reverb(dry[:, 0], 0, .4), reverb(dry[:, 1], 1, .4)], 1)
mix = wet + wh

# master envelope: fade in, duck under greeting, fade out
m_env = np.ones(N)
m_env *= np.clip(t_all / 1.2, 0, 1)
duck = np.interp(t_all, [0, 4.4, 5.4, 11.3, 13.0, DUR], [1, 1, .38, .38, 1, 1])
m_env *= duck
m_env *= np.clip((DUR - t_all) / 3.5, 0, 1) ** 1.5
mix *= m_env[:, None]

# greeting audio from the site's welcome video (0.2s ->), placed at 4.4s
with wave.open('welcome.wav') as w:
    ws = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2) / 32768.0
off = int(.2 * SR)
ws = ws[off:off + int(8.9 * SR)]
we = np.ones(len(ws)); fo = int(.9 * SR); we[-fo:] = np.linspace(1, 0, fo); fi = int(.3 * SR); we[:fi] = np.linspace(0, 1, fi)
mrms = np.sqrt(np.mean(mix[int(14 * SR):int(68 * SR)] ** 2))
mix *= 0.085 / mrms
vpk = np.max(np.abs(ws))
s = int(4.4 * SR)
mix[s:s + len(ws)] += ws * we[:, None] * (0.5 / vpk)

peak = np.max(np.abs(mix))
mix = mix / peak * .89
# gentle soft clip / glue
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
out = (mix * 32767).astype(np.int16)
with wave.open('music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print('ok', peak)
