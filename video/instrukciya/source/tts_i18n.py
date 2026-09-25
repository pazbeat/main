import json, os, sys, re, subprocess, hashlib, wave
sys.path.insert(0, '.')
from script import flow as ru_flow
from script_i18n import flow, normalise
LANG = sys.argv[1]
FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
ENG = os.environ.get('KKTTS', 'edge') if LANG == 'kk' else 'kokoro'
VD = f'voice_{LANG}' + ({'edge': '_edge', 'yandex': '_ya'}.get(ENG, ''))
os.makedirs(VD, exist_ok=True)
if LANG == 'en':
    import soundfile as sf
    from kokoro_onnx import Kokoro
    K = Kokoro('../tts/kokoro-v1.0.onnx', '../tts/voices-v1.0.bin')
    def synth(text, fn): s, sr = K.create(text, voice='af_heart', speed=1.02, lang='en-us'); sf.write(fn, s, sr)
elif ENG == 'yandex':   # Yandex SpeechKit v3, voice Amira
    import ya_tts
    YSPEED = float(os.environ.get('YASPEED', '1.3')); YVOICE = os.environ.get('YAVOICE', 'amira')
    def synth(text, fn): ya_tts.synth(text, YVOICE, fn, speed=YSPEED, host='https://tts.api.yandexcloud.kz')
elif ENG == 'edge':   # Microsoft neural voice kk-KZ-AigulNeural
    import asyncio, edge_say
    RATE = os.environ.get('KKRATE', '+0%')
    def synth(text, fn):
        mp = fn + '.mp3'; asyncio.run(edge_say.main('kk-KZ-AigulNeural', text, mp, RATE))
        subprocess.run([FF, '-loglevel', 'error', '-y', '-i', mp, fn], check=True); os.remove(mp)
else:
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    PV = PiperVoice.load('../tts/kk/kk_KZ-issai-high.onnx')
    def synth(text, fn):
        with wave.open(fn, 'wb') as w: PV.synthesize_wav(text, w, syn_config=SynthesisConfig(speaker_id=4, length_scale=0.95))
out = {}
for dev in ['pc', 'mob']:
    T = flow(dev, LANG); items = []
    for sid, kind, lines in ru_flow(dev):
        for lid, cap_ru, act, extra in lines:
            cap = T[lid]; tts = normalise(cap, LANG); h = hashlib.md5(tts.encode()).hexdigest()[:10]; fn = f'{VD}/{h}.wav'
            if not os.path.exists(fn):
                raw = fn + '.raw.wav'; synth(tts, raw)
                subprocess.run([FF,'-loglevel','error','-y','-i',raw,'-af','silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-65dB,apad=pad_dur=0.12,areverse,highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-18:TP=-2:LRA=7','-ar','48000','-ac','2',fn],check=True); os.remove(raw)
            d = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', subprocess.run([FF,'-i',fn],capture_output=True,text=True).stderr).group(3))
            items.append({'sid': sid, 'kind': kind, 'id': lid, 'cap': cap, 'tts': tts, 'act': act, 'extra': extra, 'wav': fn, 'dur': d})
    out[dev] = items
json.dump(out, open(os.environ.get('OUT', f'lines_{LANG}.json'), 'w'), ensure_ascii=False, indent=1)
for dev in out: print(LANG, dev, round(sum(i['dur'] for i in out[dev]), 1), 's speech; ru was', round(sum(i['dur'] for i in json.load(open('lines.json'))[dev]),1))
