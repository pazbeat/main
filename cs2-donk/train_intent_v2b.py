import glob, json, numpy as np, pandas as pd, lightgbm as lgb, time
from intent import INT as INT0, label, NS
INT = [f for f in INT0 if f != 'wc']
t0 = time.time()
D = pd.concat([pd.read_parquet(f, columns=list(dict.fromkeys(INT + ['fX2', 'fY2', 'frid2', 'falive2', 'rid', 'isdonk', 'tick']))).assign(match=f.split('/')[-1][:-8]) for f in sorted(glob.glob('data/fx/*.parquet'))], ignore_index=True)
D['is_scoped'] = D.is_scoped.astype(int)
ok = (D.frid2 == D.rid) & (D.falive2 == True); D = D[ok].copy(); D['cls'] = label(D.fX2.values, D.fY2.values)
PI = dict(objective='multiclass', num_class=NS + 1, learning_rate=.08, num_leaves=63, min_data_in_leaf=200, feature_fraction=.8, bagging_fraction=.5, bagging_freq=1, max_bin=127, verbose=-1, num_threads=4)
te = (D.match == 'falcons') & (D.isdonk == 1)
m = lgb.train(PI, lgb.Dataset(D.loc[D.match != 'falcons', INT], D.loc[D.match != 'falcons', 'cls']), 150)
E = D[te]; acc = float((m.predict(E[INT]).argmax(1) == E.cls).mean()); print('falcons holdout acc without weapon', round(acc, 3), f'{time.time()-t0:.0f}s', flush=True)
def flat(tr):
    feat, thr, left, right, dleft, leaf = [], [], [], [], [], []
    def walk(n):
        if 'leaf_value' in n: leaf.append(n['leaf_value']); return ~(len(leaf) - 1)
        i = len(feat); feat.append(n['split_feature']); thr.append(n['threshold']); dleft.append(1 if n.get('default_left') else 0); left.append(0); right.append(0)
        left[i] = walk(n['left_child']); right[i] = walk(n['right_child']); return i
    root = walk(tr['tree_structure']); return {'root': root, 'f': feat, 't': thr, 'l': left, 'r': right, 'd': dleft, 'v': leaf}
mi = lgb.train(dict(PI, num_leaves=31), lgb.Dataset(D[INT], D.cls), 150)
mv = D[(D.cls > 0) & (D.isdonk == 1)]
json.dump({'features': INT, 'classes': NS + 1, 'sectors': NS, 'trees': [flat(t) for t in mi.dump_model()['tree_info']], 'move_dist': int(np.hypot(mv.fX2, mv.fY2).median())},
          open('/tmp/claude-0/plug/DonkAI/donk_model.json', 'w'), separators=(',', ':'))
mi.save_model('data/intent_v2b.txt')
S = D[D.isdonk == 1].sample(300, random_state=5); pi = mi.predict(S[INT])
old = pd.read_csv('/tmp/claude-0/plug/sample.csv'); old = old.drop(columns=[c for c in old.columns if c.startswith('p') and c[1:].isdigit()])
old = old.iloc[:300].reset_index(drop=True); S = S[INT].astype(float).reset_index(drop=True)
# parity file: keep look columns from the old sample, add fresh intent rows+probs
for c in INT: old[c] = S[c]
for c in range(NS + 1): old[f'p{c}'] = pi[:, c]
old.to_csv('/tmp/claude-0/plug/sample_intent.csv', index=False)
print('EXPORTED', f'{time.time()-t0:.0f}s', flush=True)
