import json, base64, requests, sys, time
K = open('/tmp/claude-0/yandex.key').read().strip()
HOSTS = ['https://tts.api.cloud.yandex.net', 'https://tts.api.yandexcloud.kz']
def synth(text, voice, out, role=None, speed=1.0, host=None):
    hints = [{'voice': voice}, {'speed': speed}] + ([{'role': role}] if role else [])
    body = {'text': text, 'hints': hints, 'outputAudioSpec': {'containerAudio': {'containerAudioType': 'WAV'}}, 'loudnessNormalizationType': 'LUFS'}
    last = None
    for h in ([host] if host else HOSTS):
        for i in range(4):
            try:
                r = requests.post(h + '/tts/v3/utteranceSynthesis', headers={'Authorization': 'Api-Key ' + K}, json=body, timeout=120)
            except requests.exceptions.ConnectionError as e:
                last = str(e); time.sleep(2 * 2 ** i); continue
            if r.status_code != 200: last = f'{h} {r.status_code} {r.text[:300]}'; break
            audio = b''.join(base64.b64decode(json.loads(l)['result']['audioChunk']['data']) for l in r.text.splitlines() if l.strip())
            open(out, 'wb').write(audio); return h
    raise RuntimeError(last)
