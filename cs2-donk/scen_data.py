import glob, json, numpy as np, pandas as pd
M = json.load(open('data/map.json')); S = 12
ZN = json.load(open('data/zones.json'))['names']; ZG = np.load('data/zones.npy')
GROUP = {'B': ['UpperTunnel', 'OutsideTunnel', 'TunnelStairs', 'BDoors', 'BombsiteB', 'Hole', 'TRamp'],
         'Mid': ['TopofMid', 'Middle', 'MidDoors', 'Catwalk', 'ShortStairs', 'LowerTunnel'],
         'Long': ['OutsideLong', 'LongDoors', 'Pit', 'Side', 'LongA'],
         'A': ['BombsiteA', 'ARamp', 'ExtendedA', 'UnderA'], 'TSpawn': ['TSpawn'], 'CTSpawn': ['CTSpawn']}
Z2G = {z: g for g, zs in GROUP.items() for z in zs}
SITE = {'A': (1129, 2599), 'B': (-1684, 2408)}
def zone(x, y):
    cx = np.clip(((np.asarray(x) - M['x0']) // S).astype(int), 0, M['w'] - 1); cy = np.clip(((np.asarray(y) - M['y0']) // S).astype(int), 0, M['h'] - 1)
    z = ZG[cy, cx]; return np.array([ZN[i - 1] if i > 0 else '' for i in z.ravel()])
def group(z): return np.array([Z2G.get(v, 'Other') for v in z])
def load(cols, donk_only=False):
    fs = sorted(glob.glob('data/fx/*.parquet'))
    if donk_only: fs = [f for f in fs if f.split('/')[-1][:-8] in ('navi', 'aurora', '9z', 'g2', 'falcons')]
    parts = []
    for f in fs:
        k = f.split('/')[-1][:-8]; d = pd.read_parquet(f, columns=list(dict.fromkeys(cols + ['tick', 'rid', 'match'] if 'match' in cols else cols + ['tick', 'rid']))); d['match'] = k
        # bomb position for the round (planter's position at plant time)
        bpf = f'data/{k}_bomb_planted.parquet' if k in ('navi', 'aurora', '9z', 'g2', 'falcons') else f'data/x/{k}_bomb_planted.parquet'
        d['bx'] = np.nan; d['by'] = np.nan; d['btick'] = np.nan
        try:
            bp = pd.read_parquet(bpf).sort_values('tick')
            idx = np.searchsorted(bp.tick.values, d.tick.values, side='right') - 1
            okb = (idx >= 0) & (d.planted.values == 1) if 'planted' in d else idx >= 0
            d.loc[okb, 'bx'] = bp.user_X.values[idx[okb]]; d.loc[okb, 'by'] = bp.user_Y.values[idx[okb]]; d.loc[okb, 'btick'] = bp.tick.values[idx[okb]]
        except FileNotFoundError: pass
        parts.append(d)
    return pd.concat(parts, ignore_index=True)
