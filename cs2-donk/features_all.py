import os, glob, pandas as pd, numpy as np
from features import build, FEATS
KEEP = sorted(set(FEATS + ['fX2', 'fY2', 'frid2', 'falive2', 'rid', 'hok', 'yaw', 'pitch', 'match', 'name', 'tick', 'is_scoped']) - {'isdonk'})
os.makedirs('data/fx', exist_ok=True)
keys = ['navi', 'aurora', '9z', 'g2', 'falcons'] + ['x/' + os.path.basename(f).replace('_ticks.parquet', '') for f in sorted(glob.glob('data/x/*_ticks.parquet'))]
for k in keys:
    out = f"data/fx/{k.replace('x/', '')}.parquet"
    if os.path.exists(out): continue
    try:
        d = build(k)
    except Exception as ex:
        print(k, 'FAILED', str(ex)[:120], flush=True); continue
    d['isdonk'] = (d.name == 'donk').astype(np.int8)
    if not d.isdonk.any(): d = d[d.tick % 8 == 0]                 # 8 Hz is plenty for matches without donk
    d = d[KEEP + ['isdonk']]
    for c in d.columns:
        if d[c].dtype == np.float64: d[c] = d[c].astype(np.float32)
    d.to_parquet(out); print(k, len(d), flush=True)
