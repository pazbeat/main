import subprocess, os, numpy as np, pandas as pd, json
from demoparser2 import DemoParser
B = "https://huggingface.co/datasets/cs2povarchive/cs2-demos/resolve/main/iem_cologne_major_2026/"
DEMOS = {"navi": "2394900-natus-vincere-vs-spirit-iem-cologne-major/natus-vincere-vs-spirit-m1-dust2.dem", "aurora": "2394977-aurora-vs-spirit-iem-cologne-major/aurora-vs-spirit-m1-dust2.dem",
         "9z": "2394986-spirit-vs-9z-iem-cologne-major/spirit-vs-9z-m3-dust2.dem", "g2": "2394998-g2-vs-spirit-iem-cologne-major/g2-vs-spirit-m2-dust2.dem", "falcons": "2395001-spirit-vs-falcons-iem-cologne-major/spirit-vs-falcons-m3-dust2.dem"}
rows = []
for k, path in DEMOS.items():
    f = f'{k}.dem' if k != 'g2' else 'g2.dem'
    if not os.path.exists(f): subprocess.run(['curl', '-sL', '-o', f, B + path], check=True)
    p = DemoParser(f)
    deaths = p.parse_event('player_death'); fires = p.parse_event('weapon_fire')
    dk = deaths[(deaths.attacker_name == 'donk') & (deaths.user_name != 'donk')]
    donk_id = str(dk.attacker_steamid.iloc[0])
    df = fires[(fires.user_name == 'donk') & ~fires.weapon.str.contains('knife|grenade|flash|smoke|molotov|decoy|inc|c4', case=False)].tick.values
    ticks = sorted({t for kt in dk.tick for t in range(kt - 64 * 4, kt + 1)})
    T = p.parse_ticks(['approximate_spotted_by', 'X', 'Y'], ticks=ticks)
    for r in dk.itertuples():
        v = T[(T.name == r.user_name) & (T.tick <= r.tick) & (T.tick > r.tick - 64 * 4)].sort_values('tick')
        seen = np.array([donk_id in [str(s) for s in (lst if lst is not None else [])] for lst in v.approximate_spotted_by])
        shots = df[(df <= r.tick) & (df > r.tick - 64 * 3)]
        first_shot = shots.min() if len(shots) else r.tick
        # continuous "seen by donk" streak that contains the first shot (or ends at the kill)
        tk = v.tick.values; seen_at_shot = bool(seen[tk <= first_shot][-1]) if (tk <= first_shot).any() else False
        start = None
        idx = np.where(tk <= first_shot)[0]
        if len(idx) and seen[idx[-1]]:
            j = idx[-1]
            while j > 0 and seen[j - 1]: j -= 1
            start = tk[j]
        rows.append({'match': k, 'dist_m': float(r.distance), 'headshot': bool(r.headshot), 'seen_before_first_shot': seen_at_shot,
                     'reaction_s': (first_shot - start) / 64 if start is not None else None, 'shot_to_kill_s': (r.tick - first_shot) / 64,
                     'ever_seen_4s': bool(seen.any()), 'thrusmoke': bool(r.thrusmoke), 'wallbang': int(r.penetrated) > 0})
    print(k, len(dk), 'kills', flush=True)
    if k != 'g2': os.remove(f)
os.remove('g2.dem')
R = pd.DataFrame(rows); R.to_csv('data/spot_study.csv', index=False)
R['band'] = pd.cut(R.dist_m, [0, 10, 25, 100], labels=['близко <10 м', 'средне 10–25 м', 'далеко >25 м'])
g = R.groupby('band', observed=True).agg(kills=('dist_m', 'size'), seen_before_shot=('seen_before_first_shot', 'mean'), reaction_median=('reaction_s', 'median'), shot_to_kill=('shot_to_kill_s', 'median'))
print(g.round(3).to_string())
print('all: seen before first shot', round(R.seen_before_first_shot.mean(), 3), '| never seen in last 4 s', round(1 - R.ever_seen_4s.mean(), 3), '| reaction median', R.reaction_s.median(), 'p25', R.reaction_s.quantile(.25), '| wallbangs', int(R.wallbang.sum()), 'through smoke', int(R.thrusmoke.sum()))
json.dump({'by_band': g.reset_index().astype({'band': str}).to_dict('records'), 'seen_before_shot': float(R.seen_before_first_shot.mean()), 'never_seen': float(1 - R.ever_seen_4s.mean()),
           'reaction_median': float(R.reaction_s.median()), 'reaction_p25': float(R.reaction_s.quantile(.25)), 'kills': len(R), 'wallbangs': int(R.wallbang.sum()), 'smoke': int(R.thrusmoke.sum())}, open('data/spot_study.json', 'w'), ensure_ascii=False, indent=1)
