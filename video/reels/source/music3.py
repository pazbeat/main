# Sound for reel 3: notification flood (pings + buzz synced to the video), swipe, DND chime, then calm spa ambience.
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, butter, sosfilt
SR = 48000; DUR = 22.5; N = int(DUR * SR); T = np.arange(N) / SR; rng = np.random.default_rng(9)
L = np.zeros(N); R = np.zeros(N); RV = np.zeros(N)
def put(sig, t0, g=1.0, pan=0.0, rv=0.0):
    s = int(t0 * SR); n = min(len(sig), N - s)
    if n <= 0: return
    x = sig[:n] * g; L[s:s + n] += x * np.sqrt(.5 * (1 - pan)); R[s:s + n] += x * np.sqrt(.5 * (1 + pan)); RV[s:s + n] += x * rv
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def lp(x, f): return sosfilt(butter(2, f, 'lowpass', fs=SR, output='sos'), x)
def tone(f, d, dec):
    n = int(d * SR); t = np.arange(n) / SR; return (np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)) * np.exp(-t / dec) * np.minimum(1, t / .003)
PINGS = [lambda: np.concatenate([tone(1568, .09, .05), tone(2093, .25, .09)]),            # tri-tone-ish
         lambda: tone(1319, .35, .12) + .6 * tone(1976, .35, .1),
         lambda: np.concatenate([tone(1760, .07, .04), tone(1760, .2, .07)]),
         lambda: tone(2349, .3, .08)]
def buzz(d=.35):
    n = int(d * SR); t = np.arange(n) / SR
    return lp(np.sign(np.sin(2 * np.pi * 150 * t)) * (.6 + .4 * np.sin(2 * np.pi * 9 * t)), 600) * np.minimum(1, t / .02) * np.minimum(1, (d - t) / .03)
ARR = [.35 + 5.9 * (1 - (1 - k / 21) ** 1.7) for k in range(22)]
for k, a in enumerate(ARR):
    put(PINGS[k % 4](), a, .32, pan=np.sin(k * 1.7) * .5, rv=.15)
    if k % 2 == 0: put(buzz(.28 if k < 12 else .2), a + .02, .16)
# tension: rising drone + ticking clock
n = int(6.55 * SR); t = np.arange(n) / SR; k = t / t[-1]
dr = sum(np.sin(2 * np.pi * f * (1 + .05 * k) * t) for f in (55, 82.4, 110.5)) * k ** 2 * .3
dr += bp(rng.standard_normal(n), 300, 3000) * k ** 3 * .25
put(dr, 0, .5)
b = 0.0
while b < 6.4:
    put(tone(3200, .03, .006) * .8, b, .25, pan=.4); b += .5 - .25 * min(1, b / 6.4)
# swipe whoosh + silence + Do-Not-Disturb chime
n = int(.55 * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); w = np.zeros(n); seg = n // 12
for i in range(12): f = 3000 * 2 ** (-i / 3); w[i * seg:(i + 1) * seg] = bp(x[i * seg:(i + 1) * seg], f, min(f * 2.5, 20000))
put(w * np.sin(np.pi * t / t[-1]) ** 2, 6.4, .5, rv=.2)
def bell(m, d=4.0):
    n = int(d * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .6) + .25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / .25)) * np.exp(-t / 1.8) * np.minimum(1, t / .002)
put(bell(81), 6.95, .2, rv=.7); put(bell(88), 7.12, .13, pan=.4, rv=.7)
# calm: pads, water drops, slow mallet melody
def pad(ms, t0, d, g):
    n = int(d * SR); t = np.arange(n) / SR; e = np.minimum(1, t / 2.0) * np.minimum(1, np.maximum(0, (d - t) / 2.5))
    for j, m in enumerate(ms):
        s = sum(np.sin(2 * np.pi * hz(m) * (1 + dt) * t + j) for dt in (-.003, 0, .003)) / 3
        put(s * e, t0, g, pan=-.5 + j / max(1, len(ms) - 1))
pad([50, 57, 62, 66, 69], 7.4, 6.5, .05); pad([47, 54, 59, 62, 66], 12.6, 6.2, .05); pad([43, 50, 55, 59, 62, 69], 17.6, 4.9, .055)
def drop():
    n = int(.25 * SR); t = np.arange(n) / SR; f = 900 + 1400 * np.exp(-t / .02) + rng.random() * 400
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .045)
td = 7.7
while td < 21.5:
    put(drop(), td, .12, pan=rng.uniform(-.7, .7), rv=.6); td += rng.uniform(.5, 1.6)
water = bp(rng.standard_normal(N), 600, 5000) * (.5 + .5 * np.sin(2 * np.pi * .13 * T)) ** 2 * np.clip((T - 7.4) / 1.5, 0, 1) * .025
L += water; R += np.roll(water, 700)
def mallet(m, d=2.4):
    n = int(d * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / .9) + .3 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / .15)) * np.minimum(1, t / .003)
mel = [(8.6, 74), (9.4, 76), (10.4, 78), (11.2, 81), (12.4, 78), (13.2, 76), (14.9, 74), (15.5, 76), (16.1, 81), (17.0, 83), (18.4, 86), (18.9, 81), (19.6, 78), (20.4, 74)]
for t0, m in mel: put(mallet(m), t0, .14, pan=np.sin(t0) * .4, rv=.5)
for k, m in enumerate([81, 86, 88, 93]): put(bell(m, 4), 18.45 + k * .16, .07, pan=-.5 + k / 3, rv=.7)
# reverb send + master
irn = int(3.0 * SR); ti = np.arange(irn) / SR; ir = lp(rng.standard_normal((2, irn)) * np.exp(-ti / .7), 6500)
wet = np.stack([fftconvolve(RV, ir[0])[:N], fftconvolve(RV, ir[1])[:N]], 1); wet /= np.max(np.abs(wet)) + 1e-9
dry = np.stack([L, R], 1); dry /= np.max(np.abs(dry)) + 1e-9
mix = .78 * dry + .35 * wet
mix *= np.minimum(1, np.maximum(0, (DUR - T) / 1.2))[:, None]
mix /= np.max(np.abs(mix)) / .9
sf.write('music3.wav', mix, SR); print('ok')
