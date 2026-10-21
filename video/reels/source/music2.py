# Beat for reel 2 (stop-the-video card spin). 112.5 BPM so a 16th note = 4 video frames at 30 fps.
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, butter, sosfilt
SR = 48000; FPS = 30; DUR = 23.5; N = int(DUR * SR); T = np.arange(N) / SR
rng = np.random.default_rng(5); BEAT = 60 / 112.5; S16 = BEAT / 4
L = np.zeros(N); R = np.zeros(N); RV = np.zeros(N)   # RV: send to reverb
def put(sig, t0, g=1.0, pan=0.0, rv=0.0):
    s = int(t0 * SR); n = min(len(sig), N - s)
    if n <= 0 or s < 0: return
    x = sig[:n] * g; L[s:s + n] += x * np.sqrt(.5 * (1 - pan)); R[s:s + n] += x * np.sqrt(.5 * (1 + pan)); RV[s:s + n] += x * rv
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def hp(x, f): return sosfilt(butter(2, f, 'highpass', fs=SR, output='sos'), x)
def lp(x, f): return sosfilt(butter(2, f, 'lowpass', fs=SR, output='sos'), x)
def kick(d=.45):
    n = int(d * SR); t = np.arange(n) / SR; f = 48 + 110 * np.exp(-t / .035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .16) * np.minimum(1, t / .002)
def hat(d=.06, open_=False):
    n = int((.25 if open_ else d) * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t / (.08 if open_ else .018))
def snap():
    n = int(.25 * SR); t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 1200, 5000) * (np.exp(-t / .03) + .3 * np.exp(-np.maximum(0, t - .012) / .02) * (t > .012))
def tick(hi=1.0):
    n = int(.05 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2600 * hi * t) * .6 + bp(rng.standard_normal(n), 3000, 9000) * .5) * np.exp(-t / .008)
def mallet(m, d=1.4, b=1.0):
    n = int(d * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / .55) + .35 * b * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / .12) + .1 * b * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / .04)) * np.minimum(1, t / .003)
def chord(ms, d, g, cutoff=2200):
    n = int(d * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for m in ms:
        for dt in (-.004, .004):
            ph = (hz(m) * (1 + dt) * t) % 1; s += (2 * ph - 1)
    s = lp(s / len(ms), cutoff) * np.minimum(1, t / .01) * np.exp(-t / (d * .45))
    return s * g
def bass(m, d):
    n = int(d * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.minimum(1, t / .005) * np.exp(-t / (d * .9))
def whoosh(d=.5, up=True):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); out = np.zeros(n); seg = n // 16
    for i in range(16):
        f = 400 * 2 ** ((i if up else 16 - i) / 3.5); a = i * seg; out[a:a + seg] = bp(x[a:a + seg], f, min(f * 2.5, 20000))
    e = np.sin(np.pi * t / d) ** 2; return out * e
def boom():
    n = int(2.5 * SR); t = np.arange(n) / SR; f = 32 + 90 * np.exp(-t / .08)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .7) + lp(rng.standard_normal(n), 900) * np.exp(-t / .25) * .5
def chime(m, d=3.0):
    n = int(d * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .5)) * np.exp(-t / 1.2) * np.minimum(1, t / .002)
# --- timeline mirrors reel2.html ---
durs = [4] * 38 + [5, 6, 7, 9, 12, 16]; f = 0; changes = []
for d in durs: changes.append(f / FPS); f += d
LAND = f / FPS; TL = LAND + 1.6; PD = 2.2; TW = TL + 4 * PD; TC = TW + 2.8
print('LAND', round(LAND, 3), 'TL', round(TL, 3), 'TW', round(TW, 3), 'TC', round(TC, 3))
# riser through the spin
n = int((LAND - .25) * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); r = np.zeros(n); seg = n // 40
for i in range(40):
    fc = 300 * 2 ** (i / 6.5); a = i * seg; r[a:a + seg] = bp(x[a:a + seg], fc, min(fc * 1.8, 20000))
put(r * (t / t[-1]) ** 2, 0, .22, rv=.3)
sw = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (2.2 * t / t[-1])) / SR) * (t / t[-1]) ** 3; put(sw, 0, .06)
# ticks on every card change (pitch rises as the wheel slows)
for k, c in enumerate(changes): put(tick(1 + .5 * (k > 37)), c, .5 if k < 38 else .7, pan=.3 * (-1) ** k)
# driving beat 0..5 s
b = 0.0
while b < 5.0:
    put(kick(), b, .9)
    for q in range(4): put(hat(open_=(q == 2)), b + q * S16, .18 if q == 2 else .12, pan=.25)
    b += BEAT
# STOP: silence gap, then boom on landing
put(boom(), LAND, 1.0, rv=.5); put(chime(86), LAND + .05, .18, rv=.6); put(chime(93), LAND + .12, .12, pan=.5, rv=.6)
put(whoosh(.5, False), LAND - .55, .25)
# groove TL .. TW  (Dm9 - Bbmaj7 - Gm9 - A7sus), deep house
prog = [([62, 65, 69, 72, 76], 38), ([58, 62, 65, 69, 74], 34), ([55, 58, 62, 65, 69], 31), ([57, 62, 64, 67, 72], 33)]
hook = [74, 72, 69, None, 72, 69, 67, None, 69, 67, 65, 67, 69, None, 62, None]
def groove(t0, t1, full=True):
    b = t0; i = 0
    while b < t1 - .01:
        bar, beat = divmod(i, 4)
        if full: put(kick(), b, .85)
        if beat in (1, 3): put(snap(), b, .32, pan=-.15, rv=.35)
        for q in range(4):
            if full or q % 2: put(hat(open_=(q == 2)), b + q * S16, .14 if q == 2 else .08, pan=.3)
        ch, bn = prog[bar % 4]
        if beat == 0: put(chord(ch, BEAT * 3.5, .09 if full else .07, 2600 if full else 1400), b, 1, rv=.4)
        put(bass(bn, BEAT * .45), b + BEAT / 2, .35 if full else .2)
        for q in (0, 2):
            m = hook[(i * 2 + q // 2) % 16]
            if m: put(mallet(m + 12, 1.2), b + q * S16 * 2, .13, pan=.35 * np.sin(i), rv=.45)
        b += BEAT; i += 1
put(snap(), LAND + .9, .3, rv=.4)
groove(TL - BEAT, TW, True)
for k in range(4): put(whoosh(.45), TL + k * PD - .3, .22)
# wall: impact + breakdown
put(boom(), TW, .55, rv=.5); put(whoosh(.5), TW - .35, .25)
groove(TW, TC, False)
# CTA: final hit, chord, chimes
put(kick(), TC, .9); put(chord([62, 65, 69, 72, 76, 81], 3.5, .12, 2400), TC, 1, rv=.6); put(bass(38, 2.5), TC, .4)
for k, m in enumerate([81, 86, 88, 93]): put(chime(m), TC + .15 + k * .14, .1, pan=-.5 + k / 3, rv=.6)
b = TC + BEAT
while b < DUR - 1.2:
    put(snap(), b + BEAT, .18, rv=.4); put(hat(), b + S16 * 2, .07); b += 2 * BEAT
# reverb send
irn = int(2.4 * SR); ti = np.arange(irn) / SR
ir = lp(rng.standard_normal((2, irn)) * np.exp(-ti / .55), 6000)
wet = np.stack([fftconvolve(RV, ir[0])[:N], fftconvolve(RV, ir[1])[:N]], 1); wet /= np.max(np.abs(wet)) + 1e-9
dry = np.stack([L, R], 1); dry /= np.max(np.abs(dry)) + 1e-9
mix = .8 * dry + .32 * wet
mix = np.tanh(mix * 1.6) / np.tanh(1.6)   # gentle glue
mix *= np.minimum(1, np.maximum(0, (DUR - T) / 1.0))[:, None]
mix /= np.max(np.abs(mix)) / .9
sf.write('music2.wav', mix, SR); print('ok')
