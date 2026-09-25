import json, os, sys, re, subprocess, hashlib
sys.path.insert(0, '.')
from script import flow, normalise
from vosk_tts import Model, Synth
m = Model(model_path='../tts/vosk-ru'); s = Synth(m)
os.makedirs('voice', exist_ok=True)
FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
out = {}
for dev in ['pc', 'mob']:
    items = []
    for sid, kind, lines in flow(dev):
        for lid, cap, act, extra in lines:
            tts = normalise(cap); h = hashlib.md5(tts.encode()).hexdigest()[:10]
            fn = f'voice/{h}.wav'
            if not os.path.exists(fn):
                raw = f'voice/{h}_raw.wav'; s.synth(tts, raw, speaker_id=1, speech_rate=0.95)
                # trim silence edges, gentle EQ/compression, 48k stereo
                subprocess.run([FF,'-loglevel','error','-y','-i',raw,'-af','silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-65dB,apad=pad_dur=0.12,areverse,highpass=f=80,equalizer=f=3500:t=q:w=1.2:g=2,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-18:TP=-2:LRA=7','-ar','48000','-ac','2',fn],check=True)
                os.remove(raw)
            d = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', subprocess.run([FF,'-i',fn],capture_output=True,text=True).stderr).group(3))
            items.append({'sid': sid, 'kind': kind, 'id': lid, 'cap': cap, 'tts': tts, 'act': act, 'extra': extra, 'wav': fn, 'dur': d})
    out[dev] = items
json.dump(out, open('lines.json', 'w'), ensure_ascii=False, indent=1)
for dev in out: print(dev, len(out[dev]), 'lines', round(sum(i['dur'] for i in out[dev]),1), 's of speech')
