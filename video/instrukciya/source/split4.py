# Split one ElevenLabs take into per-line clips: whisper word timings + script char proportions, snapped to the widest word gap.
import sys, json, re, subprocess, numpy as np, soundfile as sf
from faster_whisper import WhisperModel
from script_v4 import TXT, line_ids, spoken
LANG = sys.argv[1]; FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
ids = line_ids(); lines = [spoken(TXT[LANG][i], LANG) for i in ids]
m = WhisperModel('medium', device='cpu', compute_type='int8')
segs, _ = m.transcribe(f'el/{LANG}.wav', language=LANG, word_timestamps=True, vad_filter=False, beam_size=5)
W = [(w.start, w.end, w.word) for s in segs for w in s.words]
norm = lambda t: re.sub(r'[\W_]+', '', t.lower())
import difflib
NUM = {'en': {'1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '100': 'onehundred', '20': 'twenty'},
       'ru': {'1': 'первый', '2': 'второй', '3': 'третий', '4': 'четвёртый', '5': 'пятый', '6': 'шестой', '100': 'ста', '20': 'двадцати'}, 'kk': {}}[LANG]
nw = [NUM.get(norm(w[2]), norm(w[2])) for w in W]
def score(j, key, endkey):
    cand = ''.join(nw[j:j + 5])[:len(key)]
    prev = ''.join(nw[max(0, j - 5):j])[-len(endkey):]
    return difflib.SequenceMatcher(None, cand, key).ratio() + difflib.SequenceMatcher(None, prev, endkey).ratio()
def wkey(words): return ''.join(NUM.get(norm(x), norm(x)) for x in words)
cuts = []; j0 = 1
for i in range(1, len(lines)):
    key = wkey(lines[i].split()[:4]); endkey = wkey(lines[i - 1].split()[-3:])
    rest = len(lines) - i
    best = max(range(j0, len(W) - rest + 1), key=lambda j: score(j, key, endkey) + (0.1 if W[j][0] - W[j - 1][1] > 0.25 else 0) - 0.001 * (j - j0))
    cuts.append((W[best - 1][1], W[best][0], best)); j0 = best + 1
a, sr = sf.read(f'el/{LANG}.wav')
def edge(t, d):   # move to the quietest 20 ms within the gap
    return t
a = a if a.ndim == 1 else a.mean(1)
def quiet(e, s):
    lo, hi = int((min(e, s) - .18) * sr), int((max(e, s) + .18) * sr); fr = int(.03 * sr)
    en = [np.sqrt(np.mean(a[k:k + fr] ** 2)) for k in range(lo, hi - fr, fr // 3)]
    return (lo + int(np.argmin(en)) * (fr // 3) + fr // 2) / sr
bounds = [0.0] + [quiet(e, s) for e, s, _ in cuts] + [len(a) / sr]
out = []
for i, lid in enumerate(ids):
    seg = a[int(bounds[i] * sr):int(bounds[i + 1] * sr)]
    fn = f'el/{LANG}_{lid}.wav'; sf.write(fn + '.raw.wav', seg, sr)
    subprocess.run([FF, '-loglevel', 'error', '-y', '-i', fn + '.raw.wav', '-af', 'silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-55dB,apad=pad_dur=0.1,areverse,afade=t=in:d=0.01,loudnorm=I=-18:TP=-2:LRA=7', '-ar', '48000', '-ac', '2', fn], check=True)
    d = sf.info(fn).duration; out.append((lid, round(d, 2)))
    txt = ''.join(w[2] for w in W if w[0] >= bounds[i] - .05 and w[1] <= bounds[i + 1] + .05)
    print(lid, round(d, 2), '|', lines[i][:50], '||', txt.strip()[:60])
gaps = [round(s - e, 2) for e, s, _ in cuts]; print('gaps', gaps)
json.dump(dict(out), open(f'el/{LANG}_dur.json', 'w'))
