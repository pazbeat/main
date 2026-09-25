import json, difflib, re
from faster_whisper import WhisperModel
w = WhisperModel("small", device="cpu", compute_type="int8")
L = json.load(open('lines.json')); seen = {}
norm = lambda s: re.sub(r'[^а-яёa-z0-9 ]', '', s.lower().replace('ё','е'))
for dev in ['pc','mob']:
    for it in L[dev]:
        if it['wav'] in seen: continue
        segs,_ = w.transcribe(it['wav'], language='ru', beam_size=5)
        hyp = ' '.join(x.text for x in segs); ref = it['tts'].replace('+','')
        r = difflib.SequenceMatcher(None, norm(ref), norm(hyp)).ratio(); seen[it['wav']] = r
        flag = '  <<<' if r < .9 else ''
        print(f"{it['id']:>4} {r:.2f} | {hyp.strip()}{flag}")
