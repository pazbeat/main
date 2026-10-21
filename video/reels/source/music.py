# Thai-spa ambient bed for the Reels ad, 24.5 s, 80 BPM: pads, ranat-like mallets, khim tremolo, ching, soft pulse.
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, butter, sosfilt
SR = 48000; DUR = 24.5; N = int(DUR * SR); T = np.arange(N) / SR
rng = np.random.default_rng(11); BEAT = 60 / 80
L = np.zeros(N); R = np.zeros(N)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def put(sig, t0, pan=0.0, g=1.0):
    s = int(t0 * SR); n = min(len(sig), N - s)
    if n <= 0: return
    L[s:s + n] += sig[:n] * g * np.sqrt(0.5 * (1 - pan)); R[s:s + n] += sig[:n] * g * np.sqrt(0.5 * (1 + pan))
def env(n, a, d):
    t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / d)
def mallet(m, dur=2.2, bright=1.0):   # ranat ek: wooden bar, strong fundamental + inharmonic partials
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9) + 0.35 * bright * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.18) \
        + 0.12 * bright * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / 0.05)
    return s * np.minimum(1, t / 0.003)
def chime(m, dur=4.0):    # glassy bell for shimmer
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .6) + .25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / .25)) * np.exp(-t / 1.6) * np.minimum(1, t / .002)
def ching(dur=2.5):       # small cymbal: band-passed noise + metallic partials
    n = int(dur * SR); t = np.arange(n) / SR
    noise = sosfilt(butter(4, [5000, 12000], 'bandpass', fs=SR, output='sos'), rng.standard_normal(n))
    met = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) for f in [3120, 4410, 5530, 7180]) / 4
    return (0.5 * noise + met) * np.exp(-t / 0.55) * np.minimum(1, t / .001)
def pad(ms, t0, dur, g):
    n = int(dur * SR); t = np.arange(n) / SR; e = np.minimum(1, t / 2.2) * np.minimum(1, np.maximum(0, (dur - t) / 2.5))
    for k, m in enumerate(ms):
        f = hz(m); s = sum(np.sin(2 * np.pi * f * (1 + d) * t + k + d * 50) for d in (-0.003, 0, 0.0035)) / 3
        s += 0.25 * np.sin(2 * np.pi * f * 2 * t)
        put(s * e * (0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t + k)), t0, pan=(-0.5 + k / max(1, len(ms) - 1)) * 0.8, g=g)
def pulse(t0, g):          # soft heartbeat kick
    n = int(.5 * SR); t = np.arange(n) / SR; f = 55 * (1 + 1.5 * np.exp(-t / .03))
    put(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .16), t0, g=g)
# D-pentatonic (Thai-like): D E F# A B
SC = [50, 52, 54, 57, 59, 62, 64, 66, 69, 71, 74, 76, 78, 81, 83]
# harmony: Dmaj9 -> Bm7 -> Gmaj7 -> Aadd9 -> Dmaj9
chords = [(0, [50, 57, 62, 64, 66]), (6, [47, 54, 59, 62, 66]), (12, [43, 50, 55, 59, 62]), (16.5, [45, 52, 57, 59, 64]), (19.5, [50, 57, 62, 66, 69])]
for i, (t0, ms) in enumerate(chords):
    t1 = chords[i + 1][0] if i + 1 < len(chords) else DUR; pad(ms, max(0, t0 - .8), t1 - t0 + 2.5, 0.05)
    put(np.sin(2 * np.pi * hz(ms[0] - 12) * np.arange(int((t1 - t0 + 1.5) * SR)) / SR) * env(int((t1 - t0 + 1.5) * SR), 1.0, 6), t0, g=0.08 if t0 >= 3 else 0.03)
# intro shimmer
for k, (t, m) in enumerate([(0.2, 81), (0.7, 86), (1.1, 83), (1.6, 88), (2.1, 90), (2.5, 86)]):
    put(chime(m), t, pan=(-0.6 if k % 2 else 0.6), g=0.05)
# ranat melody (phrase repeats with variation), 8th notes at 80 BPM
mel = [9, 8, 7, 8, 5, 7, 8, None, 9, 10, 9, 8, 7, 5, 7, None, 8, 7, 5, 4, 5, 7, 8, None, 10, 9, 8, 7, 8, 9, 10, None,
       11, 10, 9, 8, 7, 8, 9, None, 8, 7, 5, 7, 8, 7, 5, None]
t = 3.0
for k, d in enumerate(mel):
    if t > 19.2: break
    if d is not None:
        put(mallet(SC[d] + 12, bright=0.9), t, pan=0.25 * np.sin(k), g=0.11)
        if k % 4 == 0: put(mallet(SC[max(0, d - 2)] + 12, bright=.5), t + 0.012, pan=-0.3, g=0.05)
    t += BEAT / 2
# khim tremolo layer in the swell (10-19 s)
t = 10.0
while t < 19.0:
    m = SC[[5, 7, 8, 7, 9, 8, 7, 5][int((t - 10) / BEAT) % 8]] + 12
    put(mallet(m, 0.8, 0.4) * 0.6, t, pan=-0.45, g=0.035); t += BEAT / 4
# ching on beats 2 & 4 from 6 s, soft pulse from 6.5 s
b = 6.0
while b < 19.5:
    put(ching(), b + BEAT, pan=0.35, g=0.035 if b < 10 else 0.05); b += 2 * BEAT
b = 6.0
while b < 19.6:
    pulse(b, 0.22 if b < 10 else 0.32); b += BEAT
# resolution: falling arpeggio + final chimes
for k, d in enumerate([12, 10, 9, 8, 7, 5]):
    put(mallet(SC[d] + 12, 3.0), 19.6 + k * BEAT / 2, pan=0.4 * (-1) ** k, g=0.1)
for k, m in enumerate([74, 81, 86, 90]):
    put(chime(m, 5), 22.0 + k * 0.18, pan=(-0.5 + k / 3), g=0.045)
# water shimmer: filtered noise swells
w = sosfilt(butter(2, [2500, 7000], 'bandpass', fs=SR, output='sos'), rng.standard_normal(N)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * T)) ** 2 * 0.012
L += w; R += np.roll(w, 900)
# reverb: stereo exponential-noise IR
irn = int(3.2 * SR); ti = np.arange(irn) / SR
irL = rng.standard_normal(irn) * np.exp(-ti / 0.75); irR = rng.standard_normal(irn) * np.exp(-ti / 0.75)
lp = butter(2, 6500, 'lowpass', fs=SR, output='sos'); irL = sosfilt(lp, irL); irR = sosfilt(lp, irR)
wetL = fftconvolve(L, irL)[:N]; wetR = fftconvolve(R, irR)[:N]
wetL /= np.max(np.abs(wetL)) + 1e-9; wetR /= np.max(np.abs(wetR)) + 1e-9
dry = np.stack([L, R], 1); dry /= np.max(np.abs(dry)) + 1e-9
mix = 0.62 * dry + 0.42 * np.stack([wetL, wetR], 1)
fade = np.minimum(1, T / 0.4) * np.minimum(1, np.maximum(0, (DUR - T) / 2.2))
mix *= fade[:, None]; mix /= np.max(np.abs(mix)) / 0.89
sf.write('music.wav', mix, SR); print('ok', DUR)
