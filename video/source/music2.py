import numpy as np, wave

SR = 48000
DUR = 62.5
N = int(SR * DUR)
BEAT = 60 / 96
BAR = BEAT * 4
rng = np.random.default_rng(11)
T = np.arange(N) / SR


def midi(m): return 440.0 * 2 ** ((m - 69) / 12)


def place(buf, y, t0, gain=1.0, pan=.5):
    s = int(t0 * SR)
    if s >= N: return
    if s < 0: y = y[-s:]; s = 0
    n = min(len(y), N - s)
    buf[s:s + n, 0] += y[:n] * gain * (1 - pan) * 2 ** .5
    buf[s:s + n, 1] += y[:n] * gain * pan * 2 ** .5


def onepole(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); b = 1 - a
    y = np.empty_like(x); prev = 0.0
    xs = x.tolist(); out = []
    for v in xs:
        prev = b * v + a * prev; out.append(prev)
    return np.array(out)


def chunk_fb(x, D, g):
    y = x.copy()
    for i in range(D, len(y), D):
        j = min(i + D, len(y)); y[i:j] += g * y[i - D:j - D]
    return y


def allpass(x, D, g):
    xd = np.zeros_like(x); xd[D:] = x[:-D]
    return chunk_fb(-g * x + xd, D, g)


def reverb(x, seed, fb=.86):
    out = np.zeros_like(x)
    for c in [1557, 1617, 1491, 1422, 1277, 1356]:
        out += chunk_fb(x, int(c * 2.1) + seed * 29, fb)
    out /= 6
    for d in [225, 556, 441]:
        out = allpass(out, int(d * 2.1) + seed * 13, .6)
    return onepole(out, 6000)


# ---------- instruments ----------
def kick(dur=.7):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 6.5) + .15 * rng.normal(0, 1, n) * np.exp(-t * 90)


def impact(dur=4.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 32 + 70 * np.exp(-t * 7)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 1.3)
    nz = onepole(rng.normal(0, 1, n), 900) * np.exp(-t * 5) * 1.6
    return body + nz


def tabla(f0, dur=.5):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (1 + .12 * np.exp(-t * 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + .35 * np.sin(2.01 * ph)) * np.exp(-t * 11) + .25 * rng.normal(0, 1, n) * np.exp(-t * 160)


def shaker(dur=.09):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.normal(0, 1, n); x = x - onepole(x, 5000)
    return x * np.exp(-t * 60) * np.minimum(1, t / .004)


def pluck(f, dur=2.6):
    n = int(dur * SR); Np = int(SR / f)
    z = np.zeros(n + 1); b = rng.uniform(-1, 1, Np)
    b = .5 * (b + np.roll(b, 1)); z[1:Np + 1] = b
    for i in range(Np + 1, n + 1, Np):
        j = min(i + Np, n + 1); z[i:j] = .996 * .5 * (z[i - Np:j - Np] + z[i - Np - 1:j - Np - 1])
    y = z[1:]; t = np.arange(n) / SR
    y += .4 * np.sin(2 * np.pi * f * t) * np.exp(-t * 2.5)
    return y * np.exp(-t * 1.1)


def chime(f0, dur=5.0):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for r, a, d in [(1, 1, 1.3), (2.76, .5, 2.1), (5.4, .25, 3.3), (8.93, .12, 5)]:
        y += a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * d)
    return y * np.minimum(1, t / .003)


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.normal(0, 1, n); k = (t / dur) ** 2.2
    lo = onepole(x, 1500); hi = x - onepole(x, 3000)
    y = (lo * (1 - k) + hi * k) * k
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * k) / SR) * k * .25
    return y + tone


def whoosh(dur=.9):
    n = int(dur * SR); x = rng.normal(0, 1, n)
    x = onepole(x, 2500) - onepole(x, 300)
    return x * np.sin(np.linspace(0, np.pi, n)) ** 2


# ---------- tracks ----------
pad = np.zeros((N, 2)); drums = np.zeros((N, 2)); mel = np.zeros((N, 2)); fx = np.zeros((N, 2)); bass = np.zeros((N, 2))

prog = [[50, 57, 62, 66, 69, 76], [47, 54, 59, 62, 66, 73], [43, 50, 55, 59, 62, 69], [45, 52, 57, 61, 64, 71]]
roots = [38, 35, 31, 33]
scales = [[62, 64, 66, 69, 71, 74, 76, 78], [59, 61, 62, 66, 69, 71, 73, 74], [59, 62, 64, 66, 67, 69, 71, 74], [57, 59, 61, 64, 66, 69, 71, 73]]

# pad chords every 2 bars
t0 = 0.0; k = 0
while t0 < 52.5:
    notes = prog[k % 4]; length = 2 * BAR + 2.0
    n = int(length * SR); t = np.arange(n) / SR
    e = np.minimum(1, t / 1.4) * np.minimum(1, np.maximum(0, (length - t) / 2.0))
    for j, m in enumerate(notes):
        f = midi(m); sig = np.zeros(n)
        for dt in (-.08, 0, .09):
            ff = f * 2 ** (dt / 12)
            sig += np.sin(2 * np.pi * ff * t + rng.uniform(0, 6)) + .2 * np.sin(4 * np.pi * ff * t)
        sig *= e * (1 + .1 * np.sin(2 * np.pi * .15 * t + j)) * (.07 if m < 48 else .045) / 3
        place(pad, sig, t0, 1, .5 + .3 * np.sin(j * 1.7))
    t0 += 2 * BAR; k += 1
# final chord
n = int(10 * SR); t = np.arange(n) / SR
e = np.minimum(1, t / .05) * np.exp(-t * .28)
for j, m in enumerate([38, 50, 57, 62, 66, 69, 74, 78]):
    f = midi(m); sig = sum(np.sin(2 * np.pi * f * 2 ** (d / 12) * t) for d in (-.08, 0, .09)) / 3
    place(pad, sig * e * (.12 if m < 48 else .08), 52.5, 1, .5 + .3 * np.sin(j * 1.7))

# groove sections
def groove(a, b, full=True):
    tb = a
    while tb < b - 1e-6:
        bi = int(round((tb - a) / BEAT))
        # kick on 1 and the "and" of 2, and 3
        if bi % 4 == 0 or (full and bi % 4 == 2):
            place(drums, kick(), tb, .55)
        # tabla pattern on 16ths
        for s16, (f0, v) in enumerate([(0, 0), (0, 0), (210, .18), (0, 0)] if not full else [(0, 0), (320, .12), (210, .2), (320, .1)]):
            if v and rng.random() < .85:
                place(drums, tabla(f0 * (1 + .03 * rng.normal())), tb + s16 * BEAT / 4, v, .35 + .3 * rng.random())
        # shaker 8ths
        for s8 in range(2):
            place(drums, shaker(), tb + s8 * BEAT / 2 + .004 * rng.normal(), .07 if s8 else .045, .7)
        tb += BEAT

groove(12.5, 27.5, True)
groove(27.5, 35.0, False)
groove(35.0, 51.25, True)
# drum fill last bar before finale
for i in range(8):
    tt = 51.25 + i * BEAT / 2
    place(drums, tabla(180 + i * 25), tt, .12 + i * .03, .3 + .05 * i)
    if i % 2 == 0: place(drums, kick(), tt, .35 + i * .04)

# bass under grooves
for a, b in [(12.5, 27.5), (35.0, 52.5)]:
    tb = a
    while tb < b - 1e-6:
        ci = int(tb // (2 * BAR)) % 4
        f = midi(roots[ci] + 12)
        n = int(BAR * SR); t = np.arange(n) / SR
        y = (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.minimum(1, t / .02) * np.exp(-t * .9)
        place(bass, y * .16, tb, 1, .5)
        place(bass, y[:int(BEAT * 1.5 * SR)] * .1, tb + BEAT * 2.5, 1, .5)
        tb += BAR

# khim melody: 8ths with pattern, sparse in intro/voice
pattern = [0, 2, 4, 3, 5, 4, 2, 1, 3, 5, 6, 4, 7, 5, 3, 2]
tt = 12.5; i = 0
while tt < 52.4:
    ci = int(tt // (2 * BAR)) % 4; sc = scales[ci]
    dens = .45 if 27.5 <= tt < 35 else .8
    if rng.random() < dens:
        m = sc[pattern[i % 16] % len(sc)] + (12 if (i // 32) % 2 and rng.random() < .4 else 0)
        place(mel, pluck(midi(m)), tt + .006 * rng.normal(), .085 + .03 * rng.random(), .5 + .3 * np.sin(i * .9))
    tt += BEAT / 2; i += 1
# sparse notes during intro
for tt, m in [(1.2, 74), (2.4, 69), (3.1, 76), (3.9, 78), (8.2, 74), (9.4, 69), (10.6, 71)]:
    place(mel, pluck(midi(m), 3.5), tt, .07, .5)
# city bells
for j, tt in enumerate([30.0, 30.625, 31.25, 31.875, 32.5, 33.125, 33.75]):
    place(mel, chime(midi([81, 83, 85, 88, 90, 93, 95][j])), tt, .05, .3 + .07 * j)
# finale plucks
for j, (tt, m) in enumerate([(54.0, 74), (55.2, 78), (57.0, 81), (58.2, 86), (59.4, 81)]):
    place(mel, pluck(midi(m), 3.5), tt, .08, .4 + .1 * j)

# ---------- fx ----------
place(fx, riser(4.8), 0.2, .10)
place(fx, impact(), 5.0, .55)
place(fx, chime(midi(86)), 5.0, .08, .4); place(fx, chime(midi(93)), 5.05, .05, .6)
place(fx, impact(), 7.5, .3)
place(fx, riser(1.2), 11.3, .10)
for c in [12.5, 27.5, 35.0, 45.0]:
    place(fx, impact(2.5), c, .38)
for c in [15.0, 17.5, 20.0, 22.5, 25.0]:
    place(fx, whoosh(), c - .45, .09, .5 + .2 * np.sin(c))
place(fx, whoosh(1.2), 44.3, .12)
place(fx, riser(3.4), 49.1, .16)
place(fx, impact(6.0), 52.5, .75)
place(fx, chime(midi(86)), 52.5, .09, .4)
place(fx, chime(midi(90)), 57.0, .07, .6); place(fx, chime(midi(97)), 57.05, .04, .4)

# ---------- mix ----------
dry = pad * 1.0 + mel * 1.0 + drums * .9 + bass * 1.0 + fx * 1.0
send = pad * .5 + mel * .9 + drums * .25 + fx * .5
wet = np.stack([reverb(send[:, 0], 0), reverb(send[:, 1], 1)], 1)
mix = dry + wet * .55
# duck under greeting voice (7.5-12.8)
duck = np.interp(T, [0, 7.4, 7.9, 12.3, 12.9, DUR], [1, 1, .45, .45, 1, 1])
mix *= duck[:, None]
fade = np.clip(T / .8, 0, 1) * np.clip((DUR - T) / 2.2, 0, 1) ** 1.3
mix *= fade[:, None]
rms = np.sqrt(np.mean(mix[int(13 * SR):int(50 * SR)] ** 2))
mix *= .11 / rms

# greeting voice from the site's welcome video: clip 1.5s -> timeline 7.5s
with wave.open('welcome.wav') as w:
    ws = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2) / 32768.0
ws = ws[int(1.4 * SR):int(6.9 * SR)]
we = np.ones(len(ws)); fo = int(.4 * SR); we[-fo:] = np.linspace(1, 0, fo); we[:int(.05 * SR)] = np.linspace(0, 1, int(.05 * SR))
vpk = np.max(np.abs(ws))
place(mix, ws[:, 0] * we * .9 / vpk, 7.4, 1, .5)

mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix /= np.max(np.abs(mix)) / .95
out = (mix * 32767).astype(np.int16)
with wave.open('music2.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print('ok')
