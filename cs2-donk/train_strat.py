import json, numpy as np, pandas as pd, lightgbm as lgb, time
from scen_data import ZN, GROUP
from strat_data_feats import FEAT
t0 = time.time(); D = pd.read_parquet('data/strat.parquet'); NZ = len(ZN)
P = dict(objective='multiclass', num_class=NZ, learning_rate=.1, num_leaves=63, min_data_in_leaf=200, feature_fraction=.8, bagging_fraction=.5, bagging_freq=1, max_bin=127, verbose=-1, num_threads=4)
te = (D.match == 'falcons') & (D.isdonk == 1)
m = lgb.train(P, lgb.Dataset(D.loc[D.match != 'falcons', FEAT], D.loc[D.match != 'falcons', 'y']), 120)
E = D[te]; pz = m.predict(E[FEAT]).argmax(1)
Z2G = {z: g for g, zs in GROUP.items() for z in zs}; zg = np.array([Z2G.get(z, 'x') for z in ZN])
res = {'acc_zone': round(float((pz == E.y).mean()), 3), 'stay_baseline': round(float((E.zone == E.fzone).mean()), 3),
       'acc_group': round(float((zg[pz] == zg[E.y.values]).mean()), 3), 'stay_group_baseline': round(float((np.array([Z2G.get(z, 'x') for z in E.zone]) == zg[E.y.values]).mean()), 3)}
print('falcons holdout (donk)', res, f'{time.time()-t0:.0f}s', flush=True)
mf = lgb.train(P, lgb.Dataset(D[FEAT], D.y), 120); mf.save_model('data/strat_v3b.txt')
json.dump(res, open('data/strat_eval_b.json', 'w'))
print('SAVED', f'{time.time()-t0:.0f}s', flush=True)
