import os, json, subprocess, re
from demoparser2 import DemoParser
from extract import PROPS
L = json.load(open('data/dust2_list.json'))
os.makedirs('data/x', exist_ok=True)
for i, d in enumerate(L):
    key = re.sub(r'[^a-z0-9_-]', '', os.path.basename(d['path']).lower().replace('.dem', ''))
    if 'spirit' in key or os.path.exists(f'data/x/{key}_ticks.parquet') or os.path.exists(f'data/x/{key}.bad'): continue
    url = f"https://huggingface.co/datasets/{d['repo']}/resolve/main/{d['path']}"
    try:
        subprocess.run(['curl', '-sL', '--retry', '3', '-o', 'tmp.dem', url], check=True, timeout=900)
        p = DemoParser('tmp.dem')
        if p.parse_header().get('map_name') != 'de_dust2': raise Exception('not dust2')
        t = p.parse_ticks(PROPS); t = t[t.tick % 4 == 0]; t.to_parquet(f'data/x/{key}_ticks.parquet')
        for ev in ['player_death', 'weapon_fire', 'round_freeze_end', 'bomb_planted']:
            try:
                e = p.parse_event(ev, player=['X', 'Y', 'Z', 'team_num'])
                if len(e): e.to_parquet(f'data/x/{key}_{ev}.parquet')
            except Exception: pass
        print(i, key, len(t), flush=True)
    except Exception as ex:
        open(f'data/x/{key}.bad', 'w').write(str(ex)[:300]); print(i, key, 'FAILED', str(ex)[:100], flush=True)
    finally:
        if os.path.exists('tmp.dem'): os.remove('tmp.dem')
print('ALL DONE', flush=True)
