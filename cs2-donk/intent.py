import pandas as pd, numpy as np, lightgbm as lgb, json, sys
from features import FEATS
INT = [f for f in FEATS if f not in ('vx', 'vy', 'hX0_5', 'hY0_5', 'hX1', 'hY1', 'hX2', 'hY2', 'hyaw0_25', 'ysin', 'ycos', 'pitch')]
NS = 8; STAY = 120  # units in 2 s
def label(dx, dy):
    L = np.hypot(dx, dy); sec = ((np.degrees(np.arctan2(dy, dx)) + 360 + 180 / NS) % 360 // (360 / NS)).astype(int) + 1
    return np.where(L < STAY, 0, sec)
if __name__ == '__main__':
    D = pd.read_parquet('data/features.parquet'); D['is_scoped'] = D.is_scoped.astype(int)
    ok = (D.frid2 == D.rid) & (D.falive2 == True)
    D['cls'] = label(D.fX2.values, D.fY2.values)
    P = dict(objective='multiclass', num_class=NS + 1, learning_rate=.08, num_leaves=31, min_data_in_leaf=100, feature_fraction=.8, bagging_fraction=.8, bagging_freq=1, verbose=-1, num_threads=4)
    accs, base, mom = [], [], []
    for test in (['falcons'] if 'quick' in sys.argv else ['navi', 'aurora', '9z', 'g2', 'falcons']):
        tr, te = ok & (D.match != test), ok & (D.match == test) & (D.isdonk == 1)
        m = lgb.train(P, lgb.Dataset(D.loc[tr, INT], D.loc[tr, 'cls']), 150)
        E = D[te]; pr = m.predict(E[INT]).argmax(1)
        accs.append((pr == E.cls).mean()); base.append((E.cls == D.loc[tr, 'cls'].mode()[0]).mean())
        mom.append((label(E.vx.values * 2, E.vy.values * 2) == E.cls).mean())
    print(f'intent accuracy {np.mean(accs):.2f} | majority baseline {np.mean(base):.2f} | momentum (needs history) {np.mean(mom):.2f}')
    moving = D[ok & (D.cls > 0) & (D.isdonk == 1)]; print('typical 2 s distance when moving', int(np.hypot(moving.fX2, moving.fY2).median()))
    if 'export' in sys.argv:
        m = lgb.train(P, lgb.Dataset(D.loc[ok, INT], D.loc[ok, 'cls']), 150)
        def flat(tr):
            feat, thr, left, right, dleft, leaf = [], [], [], [], [], []
            def walk(n):
                if 'leaf_value' in n: leaf.append(n['leaf_value']); return ~(len(leaf) - 1)
                i = len(feat); feat.append(n['split_feature']); thr.append(n['threshold']); dleft.append(1 if n.get('default_left') else 0); left.append(0); right.append(0)
                left[i] = walk(n['left_child']); right[i] = walk(n['right_child']); return i
            root = walk(tr['tree_structure']); return {'root': root, 'f': feat, 't': thr, 'l': left, 'r': right, 'd': dleft, 'v': leaf}
        dm = m.dump_model(); trees = [flat(t) for t in dm['tree_info']]
        json.dump({'features': INT, 'classes': NS + 1, 'sectors': NS, 'trees': trees, 'move_dist': int(np.hypot(moving.fX2, moving.fY2).median())}, open('/tmp/claude-0/plug/DonkAI/donk_model.json', 'w'), separators=(',', ':'))
        m.save_model('data/intent.txt')
        S = D[D.isdonk == 1].sample(300, random_state=2)[INT].astype(float); pp = m.predict(S)
        for c in range(NS + 1): S[f'p{c}'] = pp[:, c]
        S.to_csv('/tmp/claude-0/plug/sample.csv', index=False); print('exported', len(trees), 'trees')
