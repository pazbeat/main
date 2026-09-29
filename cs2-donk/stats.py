import numpy as np, pandas as pd, json
from features import MATCHES
res = {'shots': 0, 'still': 0, 'moving_keys': 0, 'speeds': [], 'ttk': [], 'hs': 0, 'kills': 0, 'kill_dist': [], 'weapons': {}}
per_player = {}
for k in MATCHES:
    t = pd.read_parquet(f'data/{k}_ticks.parquet', columns=['tick', 'name', 'X', 'Y', 'FORWARD', 'BACK', 'LEFT', 'RIGHT', 'spotted', 'is_alive', 'is_warmup_period', 'team_num'])
    t = t[~t.is_warmup_period].sort_values(['name', 'tick'])
    t['spd'] = np.hypot(t.groupby('name').X.diff(), t.groupby('name').Y.diff()) * 16  # units/s at 16 Hz
    wf = pd.read_parquet(f'data/{k}_weapon_fire.parquet')
    wf = wf[~wf.weapon.str.contains('knife|grenade|flash|smoke|molotov|decoy|inc|c4', case=False)]
    wf['t4'] = (wf.tick // 4) * 4
    j = wf.merge(t, left_on=['user_name', 't4'], right_on=['name', 'tick'], how='inner', suffixes=('', '_t'))
    for nm, d in j.groupby('user_name'):
        pp = per_player.setdefault(nm, {'shots': 0, 'still': 0, 'keys': 0})
        pp['shots'] += len(d); pp['still'] += int((d.spd < 40).sum()); pp['keys'] += int((d.FORWARD | d.BACK | d.LEFT | d.RIGHT).sum())
    dn = j[j.user_name == 'donk']
    res['shots'] += len(dn); res['still'] += int((dn.spd < 40).sum()); res['moving_keys'] += int((dn.FORWARD | dn.BACK | dn.LEFT | dn.RIGHT).sum())
    res['speeds'] += dn.spd.dropna().round(1).tolist()
    for w, c in dn.weapon.value_counts().items(): res['weapons'][w] = res['weapons'].get(w, 0) + int(c)
    de = pd.read_parquet(f'data/{k}_player_death.parquet'); dk = de[(de.attacker_name == 'donk') & (de.user_name != 'donk')]
    res['kills'] += len(dk); res['hs'] += int(dk.headshot.sum()); res['kill_dist'] += dk.distance.round(1).tolist()
    # time from victim being spotted (continuous streak) to being killed by donk
    for _, r in dk.iterrows():
        v = t[(t.name == r.user_name) & (t.tick <= r.tick) & (t.tick > r.tick - 64 * 10)].sort_values('tick')
        if not len(v): continue
        sp = v.spotted.values[::-1]; n = 0
        for s in sp:
            if s: n += 1
            else: break
        if n: res['ttk'].append(n * 4 / 64)
out = {'donk_shots': res['shots'], 'donk_still_pct': round(100 * res['still'] / res['shots'], 1), 'donk_keys_pct': round(100 * res['moving_keys'] / res['shots'], 1),
       'donk_speed_median': float(np.median(res['speeds'])), 'kills': res['kills'], 'hs_pct': round(100 * res['hs'] / max(1, res['kills']), 1),
       'kill_dist_median_m': float(np.median(res['kill_dist'])), 'spot_to_kill_median_s': float(np.median(res['ttk'])), 'spot_to_kill_p25_s': float(np.percentile(res['ttk'], 25)),
       'weapons': dict(sorted(res['weapons'].items(), key=lambda x: -x[1])[:6]),
       'players': {n: {'shots': p['shots'], 'still_pct': round(100 * p['still'] / p['shots'], 1), 'keys_pct': round(100 * p['keys'] / p['shots'], 1)} for n, p in sorted(per_player.items(), key=lambda x: -x[1]['shots']) if p['shots'] > 150}}
json.dump(out, open('data/stats.json', 'w'), ensure_ascii=False, indent=1); print(json.dumps(out, ensure_ascii=False, indent=1))
