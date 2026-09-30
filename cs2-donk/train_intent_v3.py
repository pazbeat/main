import json, numpy as np, pandas as pd, lightgbm as lgb, time, sys
from scen_data import load
from intent import INT as INT0, label, NS
from strat_data_feats import FEAT as INT
t0 = time.time()
D = load(list(dict.fromkeys(['tick'] + [f for f in INT if f not in ('bdx', 'bdy', 'bd', 'bang', 'tp')] + ['fX2', 'fY2', 'frid2', 'falive2', 'rid', 'isdonk', 'planted'])))
D['is_scoped'] = D.is_scoped.astype(int)
D = D[(D.frid2 == D.rid) & (D.falive2 == True)].copy(); D['cls'] = label(D.fX2.values, D.fY2.values)
D['bdx'] = np.where(D.planted == 1, D.bx - D.X, 0); D['bdy'] = np.where(D.planted == 1, D.by - D.Y, 0); D['bd'] = np.where(D.planted == 1, np.hypot(D.bdx, D.bdy), 4000)
D.loc[D.planted == 1, ['bdx', 'bdy']] = D.loc[D.planted == 1, ['bdx', 'bdy']].fillna(0); D['bd'] = D.bd.fillna(4000)
D['bang'] = np.where(D.bd < 4000, np.degrees(np.arctan2(D.bdy, D.bdx)), -999)
D['tp'] = np.where((D.planted == 1) & D.btick.notna(), (D.tick - D.btick) / 64, -1)
print('rows', len(D), 'planted rows', int((D.planted == 1).sum()), f'{time.time()-t0:.0f}s', flush=True)
PI = dict(objective='multiclass', num_class=NS + 1, learning_rate=.08, num_leaves=63, min_data_in_leaf=200, feature_fraction=.8, bagging_fraction=.5, bagging_freq=1, max_bin=127, verbose=-1, num_threads=4)
te = (D.match == 'falcons') & (D.isdonk == 1)
m = lgb.train(PI, lgb.Dataset(D.loc[D.match != 'falcons', INT], D.loc[D.match != 'falcons', 'cls']), 150)
E = D[te]; print('falcons holdout acc', round(float((m.predict(E[INT]).argmax(1) == E.cls).mean()), 3), f'{time.time()-t0:.0f}s', flush=True)
mi = lgb.train(PI, lgb.Dataset(D[INT], D.cls), 150); mi.save_model('data/intent_v3b.txt')
def flat(tr):
    feat, thr, left, right, dleft, leaf = [], [], [], [], [], []
    def walk(n):
        if 'leaf_value' in n: leaf.append(n['leaf_value']); return ~(len(leaf) - 1)
        i = len(feat); feat.append(n['split_feature']); thr.append(n['threshold']); dleft.append(1 if n.get('default_left') else 0); left.append(0); right.append(0)
        left[i] = walk(n['left_child']); right[i] = walk(n['right_child']); return i
    root = walk(tr['tree_structure']); return {'root': root, 'f': feat, 't': thr, 'l': left, 'r': right, 'd': dleft, 'v': leaf}
mv = D[(D.cls > 0) & (D.isdonk == 1)]
json.dump({'features': INT, 'classes': NS + 1, 'sectors': NS, 'trees': [flat(t) for t in mi.dump_model()['tree_info']], 'move_dist': int(np.hypot(mv.fX2, mv.fY2).median())},
          open('/tmp/claude-0/plug/DonkAI/donk_model.json', 'w'), separators=(',', ':'))
S = D[D.isdonk == 1].sample(300, random_state=6); pi = mi.predict(S[INT]); S = S[INT].astype(float).reset_index(drop=True)
for c in range(NS + 1): S[f'p{c}'] = pi[:, c]
S.to_csv('/tmp/claude-0/plug/sample_intent.csv', index=False); print('EXPORTED', f'{time.time()-t0:.0f}s', flush=True)
