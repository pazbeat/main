import numpy as np, wave

SR = 48000
DUR = 25.0
N = int(SR * DUR)
BEAT = 60 / 96
BAR = BEAT * 4
rng = np.random.default_rng(23)
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



pad = np.zeros((N, 2)); drums = np.zeros((N, 2)); mel = np.zeros((N, 2)); fx = np.zeros((N, 2)); bass = np.zeros((N, 2))
prog = [[50, 57, 62, 66, 69, 76], [47, 54, 59, 62, 66, 73], [43, 50, 55, 59, 62, 69], [45, 52, 57, 61, 64, 71]]
roots = [38, 35, 31, 33]
scales = [[62, 64, 66, 69, 71, 74, 76, 78], [59, 61, 62, 66, 69, 71, 73, 74], [59, 62, 64, 66, 67, 69, 71, 74], [57, 59, 61, 64, 66, 69, 71, 73]]
t0 = 0.0; k = 0
while t0 < 20:
    notes = prog[k % 4]; length = 2 * BAR + 1.5
    n = int(length * SR); t = np.arange(n) / SR
    e = np.minimum(1, t / (0.25 if t0 == 0 else 1.0)) * np.minimum(1, np.maximum(0, (length - t) / 1.5))
    for j, m in enumerate(notes):
        f = midi(m); sig = np.zeros(n)
        for dt in (-.08, 0, .09):
            sig += np.sin(2 * np.pi * f * 2 ** (dt / 12) * t + rng.uniform(0, 6)) + .2 * np.sin(4 * np.pi * f * 2 ** (dt / 12) * t)
        sig *= e * (1 + .1 * np.sin(2 * np.pi * .15 * t + j)) * (.07 if m < 48 else .045) / 3
        place(pad, sig, t0, 1, .5 + .3 * np.sin(j * 1.7))
    t0 += 2 * BAR; k += 1
n = int(6 * SR); t = np.arange(n) / SR
e = np.minimum(1, t / .05) * np.exp(-t * .3)
for j, m in enumerate([38, 50, 57, 62, 66, 69, 74, 78]):
    f = midi(m); sig = sum(np.sin(2 * np.pi * f * 2 ** (d / 12) * t) for d in (-.08, 0, .09)) / 3
    place(pad, sig * e * (.12 if m < 48 else .08), 20.0, 1, .5 + .3 * np.sin(j * 1.7))

def groove(a, b, full=True):
    tb = a
    while tb < b - 1e-6:
        bi = int(round((tb - a) / BEAT))
        if bi % 4 == 0 or (full and bi % 4 == 2): place(drums, kick(), tb, .6)
        pat = [(0, 0), (320, .12), (210, .2), (320, .1)] if full else [(0, 0), (0, 0), (210, .16), (0, 0)]
        for s16, (f0, v) in enumerate(pat):
            if v and rng.random() < .85: place(drums, tabla(f0 * (1 + .03 * rng.normal())), tb + s16 * BEAT / 4, v, .35 + .3 * rng.random())
        for s8 in range(2): place(drums, shaker(), tb + s8 * BEAT / 2 + .004 * rng.normal(), .07 if s8 else .045, .7)
        tb += BEAT
groove(3.75, 7.5, False)
groove(7.5, 17.5, True)
groove(17.5, 18.75, False)
for i in range(8):
    tt = 18.75 + i * BEAT / 4 * 1.0
    place(drums, tabla(180 + i * 30), tt, .1 + i * .025, .3 + .05 * i)
for a, b in [(7.5, 20.0)]:
    tb = a
    while tb < b - 1e-6:
        ci = int(tb // (2 * BAR)) % 4; f = midi(roots[ci] + 12)
        n = int(BAR * SR); t = np.arange(n) / SR
        y = (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.minimum(1, t / .02) * np.exp(-t * .9)
        place(bass, y * .17, tb, 1, .5); place(bass, y[:int(BEAT * 1.5 * SR)] * .1, tb + BEAT * 2.5, 1, .5)
        tb += BAR
pattern = [0, 2, 4, 3, 5, 4, 2, 1, 3, 5, 6, 4, 7, 5, 3, 2]
tt = 3.75; i = 0
while tt < 19.9:
    ci = int(tt // (2 * BAR)) % 4; sc = scales[ci]
    if rng.random() < (.55 if tt < 7.5 else .85):
        m = sc[pattern[i % 16] % len(sc)] + (12 if (i // 16) % 2 and rng.random() < .4 else 0)
        place(mel, pluck(midi(m)), tt + .006 * rng.normal(), .085 + .03 * rng.random(), .5 + .3 * np.sin(i * .9))
    tt += BEAT / 2; i += 1
for j in range(7):
    place(mel, chime(midi([81, 83, 85, 88, 90, 93, 95][j])), 17.95 + j * .15, .045, .3 + .07 * j)
for j, (tt, m) in enumerate([(20.6, 74), (21.3, 78), (22.6, 81), (23.4, 86), (24.1, 81)]):
    place(mel, pluck(midi(m), 3.5), tt, .085, .4 + .1 * j)
place(fx, impact(2.0), 0.0, .3)
place(fx, chime(midi(93)), 0.02, .05, .6)
place(fx, riser(1.9), 0.05, .12)
place(fx, impact(), 1.95, .6)
place(fx, chime(midi(86)), 1.95, .08, .4); place(fx, chime(midi(93)), 2.0, .05, .6)
for c in [3.75, 7.5, 13.75, 17.5]: place(fx, impact(2.2), c, .4)
for c in [8.75, 10.0, 11.25, 12.5]:
    place(fx, whoosh(.7), c - .4, .11, .5 + .25 * np.sin(c)); place(fx, impact(1.0), c, .16)
place(fx, whoosh(.9), 7.1, .12)
place(fx, riser(1.8), 18.2, .16)
place(fx, impact(5.0), 20.0, .75)
place(fx, chime(midi(86)), 20.0, .09, .4)
place(fx, chime(midi(90)), 22.6, .07, .6); place(fx, chime(midi(97)), 22.65, .04, .4)
dry = pad + mel + drums * .9 + bass + fx
send = pad * .5 + mel * .9 + drums * .25 + fx * .5
wet = np.stack([reverb(send[:, 0], 0), reverb(send[:, 1], 1)], 1)
mix = dry + wet * .55
fade = np.clip(T / .02, 0, 1) * np.clip((DUR - T) / .8, 0, 1) ** 1.2
mix *= fade[:, None]
rms = np.sqrt(np.mean(mix[int(4 * SR):int(19 * SR)] ** 2)); mix *= .12 / rms
mix = np.tanh(mix * 1.2) / np.tanh(1.2); mix /= np.max(np.abs(mix)) / .95
out = (mix * 32767).astype(np.int16)
with wave.open('music3.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print('ok')
