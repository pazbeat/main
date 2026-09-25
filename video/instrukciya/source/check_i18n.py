import json, difflib, re, sys
from faster_whisper import WhisperModel
LANG = sys.argv[1]; w = WhisperModel('small' if LANG == 'en' else 'medium', device='cpu', compute_type='int8')
L = json.load(open(f'lines_{LANG}.json')); seen = set(); rs = []
norm = lambda s: re.sub(r'[^\w ]', '', s.lower())
for it in L['pc'] + L['mob']:
    if it['wav'] in seen: continue
    seen.add(it['wav']); segs, _ = w.transcribe(it['wav'], language=LANG, beam_size=5); hyp = ' '.join(x.text for x in segs).strip()
    r = difflib.SequenceMatcher(None, norm(it['tts']), norm(hyp)).ratio(); rs.append(r)
    print(f"{it['id']:>3} {r:.2f} | {hyp}" + ('   <<<' if r < .8 else ''))
print('mean', round(sum(rs) / len(rs), 3))
