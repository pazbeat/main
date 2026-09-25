import json, sys, wave, numpy as np
sys.path.insert(0, '..')
DEV = sys.argv[1]; SR = 48000
P = json.load(open(f'plan_{DEV}.json')); N = int((P['total'] + 0.5) * SR)
def readwav(fn):
    with wave.open(fn) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, w.getnchannels()) / 32768.0
    return a if a.shape[1] == 2 else np.repeat(a, 2, 1)
voice = np.zeros((N, 2))
for l in P['lines']:
    a = readwav(l['wav']); s = int(l['voice'] * SR); n = min(len(a), N - s); voice[s:s + n] += a[:n]
# soft ambient bed: slow pad chords + sparse plucks
rng = np.random.default_rng(5); T = np.arange(N) / SR
def midi(m): return 440 * 2 ** ((m - 69) / 12)
prog = [[50, 57, 62, 66, 69], [47, 54, 59, 62, 66], [43, 50, 55, 59, 62], [45, 52, 57, 61, 64]]
bed = np.zeros(N); CH = 8.0
for i, t0 in enumerate(np.arange(0, P['total'] + CH, CH)):
    s = int(t0 * SR); n = min(int((CH + 3) * SR), N - s)
    if n <= 0: break
    t = np.arange(n) / SR; e = np.minimum(1, t / 2.5) * np.minimum(1, np.maximum(0, (CH + 3 - t) / 3))
    for j, m in enumerate(prog[i % 4]):
        f = midi(m); bed[s:s + n] += (np.sin(2 * np.pi * f * t + j) + .3 * np.sin(2 * np.pi * f * 1.003 * t)) * e * (.05 if m < 48 else .03)
for k in range(int(P['total'] / 1.6)):
    tt = k * 1.6 + rng.random() * .3
    if rng.random() < .45:
        f = midi([74, 76, 78, 81, 83, 86][int(rng.random() * 6)]); n = int(2.5 * SR); s = int(tt * SR)
        if s + n < N: t = np.arange(n) / SR; bed[s:s + n] += np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) * np.minimum(1, t / .01) * .03
# simple feedback reverb for the bed
out = bed.copy()
for D, g in [(int(.113 * SR), .5), (int(.171 * SR), .45), (int(.237 * SR), .4)]:
    y = out.copy()
    for i in range(D, len(y), D): j = min(i + D, len(y)); y[i:j] += g * y[i - D:j - D]
    out = .6 * out + .4 * y
bed = out / (np.max(np.abs(out)) + 1e-9)
# level: bed ~ 22 dB under the voice; gentle ducking while speaking
vrms = np.sqrt(np.mean(voice[voice != 0] ** 2)) if np.any(voice) else .1
env = np.convolve((np.abs(voice[:, 0]) > .02).astype(float), np.ones(int(.4 * SR)) / int(.4 * SR), 'same')
bed *= vrms * 10 ** (-19 / 20) / (np.sqrt(np.mean(bed ** 2)) + 1e-9) * (1 - .35 * np.clip(env * 3, 0, 1))
fade = np.clip(T / 1.5, 0, 1) * np.clip((P['total'] + .5 - T) / 2.0, 0, 1)
mix = voice + np.stack([bed, bed], 1) * fade[:, None]
mix /= max(1, np.max(np.abs(mix)) / .95)
with wave.open(f'audio_{DEV}.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
print('ok', DEV)
