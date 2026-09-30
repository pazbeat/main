# zone where the player will be in 10 s (same round, still alive) -> "strategy" target
import glob, numpy as np, pandas as pd, json
from scen_data import zone, ZN
from intent import INT as INT0
from strat_data_feats import FEAT
parts = []
for f in sorted(glob.glob('data/fx/*.parquet')):
    k = f.split('/')[-1][:-8]; donk = k in ('navi', 'aurora', '9z', 'g2', 'falcons')
    d = pd.read_parquet(f, columns=list(dict.fromkeys([c for c in FEAT if c not in ('bdx', 'bdy', 'bd', 'bang', 'tp')] + ['name', 'tick', 'rid', 'planted'])))
    d['match'] = k
    bpf = f'data/{k}_bomb_planted.parquet' if donk else f'data/x/{k}_bomb_planted.parquet'
    d['bx'] = np.nan; d['by'] = np.nan; d['btick'] = np.nan
    try:
        bp = pd.read_parquet(bpf).sort_values('tick'); idx = np.searchsorted(bp.tick.values, d.tick.values, side='right') - 1; okb = (idx >= 0) & (d.planted.values == 1)
        d.loc[okb, 'bx'] = bp.user_X.values[idx[okb]]; d.loc[okb, 'by'] = bp.user_Y.values[idx[okb]]; d.loc[okb, 'btick'] = bp.tick.values[idx[okb]]
    except FileNotFoundError: pass
    d = d.sort_values(['name', 'tick'])
    fut = d[['name', 'tick', 'rid', 'X', 'Y']].rename(columns={'tick': 'ftick', 'rid': 'frid', 'X': 'fx', 'Y': 'fy'}); fut['tick'] = fut.ftick - 640
    d = d.merge(fut[['name', 'tick', 'frid', 'fx', 'fy']], on=['name', 'tick'], how='left')
    d = d[(d.frid == d.rid)]
    if not donk: d = d[d.tick % 16 == 0]                                   # 4 Hz is enough for other teams
    d['fzone'] = zone(d.fx.values, d.fy.values); d['zone'] = zone(d.X.values, d.Y.values)
    parts.append(d.drop(columns=['frid']))
D = pd.concat(parts, ignore_index=True)
D['bdx'] = np.where(D.planted == 1, D.bx - D.X, 0); D['bdy'] = np.where(D.planted == 1, D.by - D.Y, 0)
D.loc[D.planted == 1, ['bdx', 'bdy']] = D.loc[D.planted == 1, ['bdx', 'bdy']].fillna(0)
D['bd'] = np.where(D.planted == 1, np.hypot(D.bdx, D.bdy), 4000); D['bang'] = np.where(D.planted == 1, np.degrees(np.arctan2(D.bdy, D.bdx)), -999)
D['tp'] = np.where((D.planted == 1) & D.btick.notna(), (D.tick - D.btick) / 64, -1)
D['is_scoped'] = D.is_scoped.astype(int); D['isdonk'] = (D.name == 'donk').astype(int)
D['y'] = D.fzone.map({z: i for i, z in enumerate(ZN)}).astype(int)
for c in D.columns:
    if D[c].dtype == np.float64: D[c] = D[c].astype(np.float32)
D.to_parquet('data/strat.parquet'); print(len(D), 'rows; donk rows', int(D.isdonk.sum()), '; stays in same zone', round(float((D.zone == D.fzone).mean()), 3))
