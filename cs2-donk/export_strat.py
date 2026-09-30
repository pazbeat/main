import json, numpy as np, pandas as pd, lightgbm as lgb
from scen_data import ZN, zone, M
from strat_data_feats import FEAT
def flat(tr):
    feat, thr, left, right, dleft, leaf = [], [], [], [], [], []
    def walk(n):
        if 'leaf_value' in n: leaf.append(n['leaf_value']); return ~(len(leaf) - 1)
        i = len(feat); feat.append(n['split_feature']); thr.append(n['threshold']); dleft.append(1 if n.get('default_left') else 0); left.append(0); right.append(0)
        left[i] = walk(n['left_child']); right[i] = walk(n['right_child']); return i
    root = walk(tr['tree_structure']); return {'root': root, 'f': feat, 't': thr, 'l': left, 'r': right, 'd': dleft, 'v': leaf}
m = lgb.Booster(model_file='data/strat_v3b.txt'); assert m.feature_name() == FEAT
D = pd.read_parquet('data/strat.parquet', columns=['X', 'Y', 'zone'])
D['cx'] = ((D.X - M['x0']) // 48).astype(int); D['cy'] = ((D.Y - M['y0']) // 48).astype(int)   # 4x4-cell buckets
targets = []
for z in ZN:
    q = D[D.zone == z]; b = q.groupby(['cx', 'cy']).size().idxmax(); qq = q[(q.cx == b[0]) & (q.cy == b[1])]
    targets.append([round(float(qq.X.median()), 1), round(float(qq.Y.median()), 1)])
json.dump({'features': FEAT, 'zones': ZN, 'targets': targets, 'trees': [flat(t) for t in m.dump_model()['tree_info']]}, open('/tmp/claude-0/plug/DonkAI/donk_strat.json', 'w'), separators=(',', ':'))
S = pd.read_parquet('data/strat.parquet').query('isdonk == 1').sample(300, random_state=7); p = m.predict(S[FEAT]); S = S[FEAT].astype(float).reset_index(drop=True)
for c in range(len(ZN)): S[f's{c}'] = p[:, c]
S.to_csv('/tmp/claude-0/plug/sample_strat.csv', index=False)
print('exported', len(ZN), 'zones;', dict(zip(ZN, targets)))
