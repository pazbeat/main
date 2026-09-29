import numpy as np, pandas as pd, lightgbm as lgb, json
from sklearn.metrics import roc_auc_score
from features import FEATS, MATCHES
D = pd.read_parquet('data/features.parquet')
for c in ('is_scoped',): D[c] = D[c].astype(int)
ok2 = (D.frid2 == D.rid) & (D.falive2 == True); ok1 = (D.frid1 == D.rid) & (D.falive1 == True)
P = dict(objective='huber', alpha=60, learning_rate=.05, num_leaves=63, min_data_in_leaf=80, feature_fraction=.8, bagging_fraction=.8, bagging_freq=1, verbose=-1, num_threads=4)
U = 2.54 / 100  # game unit -> metres
res = {h: {'model': [], 'model_donk_only': [], 'const_vel': [], 'stay': []} for h in ('1', '2')}
res['yaw'] = {'model': [], 'keep': [], 'const_turn': []}; res['fire_auc'] = []
preds = []
for test in MATCHES:
    tr, te = D.match != test, (D.match == test) & (D.isdonk == 1)
    for h, ok in (('1', ok1), ('2', ok2)):
        T = int(h)
        mx = lgb.train(P, lgb.Dataset(D.loc[tr & ok, FEATS], D.loc[tr & ok, f'fX{h}']), 400)
        my = lgb.train(P, lgb.Dataset(D.loc[tr & ok, FEATS], D.loc[tr & ok, f'fY{h}']), 400)
        dd = tr & ok & (D.isdonk == 1)
        mxd = lgb.train(P, lgb.Dataset(D.loc[dd, FEATS], D.loc[dd, f'fX{h}']), 400); myd = lgb.train(P, lgb.Dataset(D.loc[dd, FEATS], D.loc[dd, f'fY{h}']), 400)
        E = D[te & ok]; gx, gy = E[f'fX{h}'].values, E[f'fY{h}'].values
        px, py = mx.predict(E[FEATS]), my.predict(E[FEATS])
        err = lambda a, b: np.hypot(a - gx, b - gy) * U
        res[h]['model'] += err(px, py).tolist(); res[h]['model_donk_only'] += err(mxd.predict(E[FEATS]), myd.predict(E[FEATS])).tolist()
        res[h]['const_vel'] += err(E.vx.values * T, E.vy.values * T).tolist(); res[h]['stay'] += err(0 * gx, 0 * gy).tolist()
        if h == '2': preds.append(pd.DataFrame({'match': test, 'rid': E.rid.values, 'tick': E.tick.values, 'X': E.X.values, 'Y': E.Y.values, 'gx': gx, 'gy': gy, 'px': px, 'py': py, 'cvx': E.vx.values * 2, 'cvy': E.vy.values * 2, 'team': E.team_num.values}))
    oky = D.fyaw0_5.notna() & ok1
    myw = lgb.train(P | {'alpha': 8}, lgb.Dataset(D.loc[tr & oky, FEATS], D.loc[tr & oky, 'fyaw0_5']), 400)
    E = D[te & oky]; g = E.fyaw0_5.values
    res['yaw']['model'] += np.abs(myw.predict(E[FEATS]) - g).tolist(); res['yaw']['keep'] += np.abs(g).tolist(); res['yaw']['const_turn'] += np.abs(E.hyaw0_25.values * 2 - g).tolist()
    mf = lgb.train(dict(P, objective='binary'), lgb.Dataset(D.loc[tr, FEATS], D.loc[tr, 'ffire']), 300)
    E = D[te]; res['fire_auc'].append(roc_auc_score(E.ffire, mf.predict(E[FEATS])))
    print(test, 'done', flush=True)
summ = {}
for h in ('1', '2'): summ[f'pos_{h}s'] = {k: {'median_m': round(float(np.median(v)), 2), 'mean_m': round(float(np.mean(v)), 2)} for k, v in res[h].items()}
summ['yaw_0_5s'] = {k: {'median_deg': round(float(np.median(v)), 1), 'mean_deg': round(float(np.mean(v)), 1)} for k, v in res['yaw'].items()}
summ['fire_auc'] = [round(a, 3) for a in res['fire_auc']]; summ['fire_auc_mean'] = round(float(np.mean(res['fire_auc'])), 3)
imp = pd.Series(mx.feature_importance('gain'), FEATS).sort_values(ascending=False); summ['top_features_pos'] = (imp / imp.sum()).round(3).head(10).to_dict()
json.dump(summ, open('data/results.json', 'w'), indent=1); print(json.dumps(summ, indent=1))
pd.concat(preds).to_parquet('data/preds.parquet')
