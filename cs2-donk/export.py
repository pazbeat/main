import numpy as np, pandas as pd, json, base64
pr = pd.read_parquet('data/preds.parquet'); M = json.load(open('data/map.json'))
rounds = []
for (mt, rid), d in pr.groupby(['match', 'rid']):
    if len(d) < 16 * 18: continue
    rounds.append((mt, rid, len(d), int(d.team.iloc[0])))
rounds.sort(key=lambda r: -r[2])
pick = []
for side in (2, 3):
    pick += [r for r in rounds if r[3] == side][:3]
out = []
opp = {'navi': 'NAVI', 'aurora': 'Aurora', '9z': '9z', 'g2': 'G2', 'falcons': 'Falcons'}
for mt, rid, n, side in pick:
    d = pr[(pr.match == mt) & (pr.rid == rid)].sort_values('tick')
    t = pd.read_parquet(f'data/{mt}_ticks.parquet', columns=['tick', 'name', 'X', 'Y', 'team_num', 'is_alive'])
    t = t[(t.tick >= d.tick.min()) & (t.tick <= d.tick.max() + 128) & t.is_alive & (t.name != 'donk')]
    others = {int(tk): [[round(x), round(y), int(tm == side)] for x, y, tm in zip(g.X, g.Y, g.team_num)] for tk, g in t.groupby('tick')}
    fr = [[int(tk), round(x), round(y), round(x + px), round(y + py), round(x + cx), round(y + cy)] for tk, x, y, px, py, cx, cy in zip(d.tick, d.X, d.Y, d.px, d.py, d.cvx, d.cvy)]
    out.append({'match': opp[mt], 'round': int(rid), 'side': 'T' if side == 2 else 'CT', 'frames': fr, 'others': [others.get(f[0], []) for f in fr]})
# donk heat per side (all matches)
heat = {}
for side in (2, 3):
    xs, ys = [], []
    for mt in ['navi', 'aurora', '9z', 'g2', 'falcons']:
        t = pd.read_parquet(f'data/{mt}_ticks.parquet', columns=['name', 'X', 'Y', 'team_num', 'is_alive', 'is_freeze_period', 'is_warmup_period'])
        t = t[(t.name == 'donk') & t.is_alive & ~t.is_freeze_period & ~t.is_warmup_period & (t.team_num == side)]
        xs.append(t.X.values); ys.append(t.Y.values)
    X, Y = np.concatenate(xs), np.concatenate(ys)
    H, _, _ = np.histogram2d(Y, X, bins=[M['h'] // 3, M['w'] // 3], range=[[M['y0'], M['y1']], [M['x0'], M['x1']]])
    heat['T' if side == 2 else 'CT'] = (H / H.max()).round(3).tolist()
json.dump({'map': M, 'mapimg': 'data:image/png;base64,' + base64.b64encode(open('data/map.png', 'rb').read()).decode(), 'rounds': out, 'heat': heat,
           'results': json.load(open('data/results.json')), 'stats': json.load(open('data/stats.json'))}, open('data/page.json', 'w'), separators=(',', ':'))
print([(r['match'], r['round'], r['side'], len(r['frames'])) for r in out])
