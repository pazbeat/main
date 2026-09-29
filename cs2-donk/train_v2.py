import glob, json, numpy as np, pandas as pd, lightgbm as lgb, time
from intent import INT, label, NS
from look import LOOK, NB, circ_err
t0 = time.time()
parts = []
for f in sorted(glob.glob('data/fx/*.parquet')):
    d = pd.read_parquet(f); d['match'] = f.split('/')[-1][:-8]; parts.append(d)
D = pd.concat(parts, ignore_index=True); del parts
D['is_scoped'] = D.is_scoped.astype(int); D['hok'] = D.hok.astype(bool)
ok = (D.frid2 == D.rid) & (D.falive2 == True)
D['cls'] = -1; D.loc[ok, 'cls'] = label(D.loc[ok, 'fX2'].values, D.loc[ok, 'fY2'].values)
D['ybin'] = (((D.yaw + 360 + 180 / NB) % 360) // (360 / NB)).astype(int) % NB
DONK = ['navi', 'aurora', '9z', 'g2', 'falcons']
print('rows', len(D), 'matches', D.match.nunique(), 'donk rows', int(D.isdonk.sum()), f'{time.time()-t0:.0f}s', flush=True)
PI = dict(objective='multiclass', num_class=NS + 1, learning_rate=.08, num_leaves=63, min_data_in_leaf=200, feature_fraction=.8, bagging_fraction=.5, bagging_freq=1, max_bin=127, verbose=-1, num_threads=4)
PL = dict(objective='multiclass', num_class=NB, learning_rate=.1, num_leaves=31, min_data_in_leaf=200, feature_fraction=.8, bagging_fraction=.4, bagging_freq=1, max_bin=127, verbose=-1, num_threads=4)
PP = dict(objective='huber', alpha=5, learning_rate=.08, num_leaves=31, min_data_in_leaf=200, max_bin=127, verbose=-1, num_threads=4)
look_rows = D.hok & D.yaw.notna() & ((D.isdonk == 1) | (D.tick % 16 == 0) | D.match.isin(DONK))
res = {'intent_5': [], 'intent_all': [], 'look_all': [], 'pitch_all': []}
for test in ['falcons', 'g2']:
    te = (D.match == test) & (D.isdonk == 1)
    for key, pool in (('intent_5', D.match.isin(DONK)), ('intent_all', D.match == D.match)):
        tr = ok & pool & (D.match != test)
        m = lgb.train(PI, lgb.Dataset(D.loc[tr, INT], D.loc[tr, 'cls']), 150)
        E = D[te & ok]; res[key] += list(m.predict(E[INT]).argmax(1) == E.cls.values)
        print(test, key, f'{np.mean(res[key]):.3f}', f'{time.time()-t0:.0f}s', flush=True)
    tr = look_rows & (D.match != test)
    m = lgb.train(PL, lgb.Dataset(D.loc[tr, LOOK], D.loc[tr, 'ybin']), 100)
    E = D[te & D.hok & D.yaw.notna()]; pb = m.predict(E[LOOK]).argmax(1) * (360 / NB); pb = np.where(pb > 180, pb - 360, pb)
    res['look_all'] += list(circ_err(pb, E.yaw.values))
    mp = lgb.train(PP, lgb.Dataset(D.loc[tr, LOOK], D.loc[tr, 'pitch']), 150); res['pitch_all'] += list(np.abs(mp.predict(E[LOOK]) - E.pitch))
    print(test, 'look within15', f"{np.mean(np.array(res['look_all']) <= 15):.3f}", f'{time.time()-t0:.0f}s', flush=True)
summary = {'intent_acc_5matches': round(float(np.mean(res['intent_5'])), 3), 'intent_acc_70matches': round(float(np.mean(res['intent_all'])), 3),
           'look_within15_70matches': round(float(np.mean(np.array(res['look_all']) <= 15)), 3), 'look_median_err': round(float(np.median(res['look_all'])), 1),
           'pitch_mae_70matches': round(float(np.mean(res['pitch_all'])), 2), 'rows': int(len(D)), 'matches': int(D.match.nunique())}
print(json.dumps(summary, indent=1), flush=True); json.dump(summary, open('data/results_v2.json', 'w'), indent=1)
# final models on everything
def flat(tr):
    feat, thr, left, right, dleft, leaf = [], [], [], [], [], []
    def walk(n):
        if 'leaf_value' in n: leaf.append(n['leaf_value']); return ~(len(leaf) - 1)
        i = len(feat); feat.append(n['split_feature']); thr.append(n['threshold']); dleft.append(1 if n.get('default_left') else 0); left.append(0); right.append(0)
        left[i] = walk(n['left_child']); right[i] = walk(n['right_child']); return i
    root = walk(tr['tree_structure']); return {'root': root, 'f': feat, 't': thr, 'l': left, 'r': right, 'd': dleft, 'v': leaf}
moving = D[ok & (D.cls > 0) & (D.isdonk == 1)]
mi = lgb.train(dict(PI, num_leaves=31), lgb.Dataset(D.loc[ok, INT], D.loc[ok, 'cls']), 150)
json.dump({'features': INT, 'classes': NS + 1, 'sectors': NS, 'trees': [flat(t) for t in mi.dump_model()['tree_info']], 'move_dist': int(np.hypot(moving.fX2, moving.fY2).median())},
          open('/tmp/claude-0/plug/DonkAI/donk_model.json', 'w'), separators=(',', ':'))
ml = lgb.train(dict(PL, num_leaves=24), lgb.Dataset(D.loc[look_rows, LOOK], D.loc[look_rows, 'ybin']), 100)
mp = lgb.train(PP, lgb.Dataset(D.loc[look_rows, LOOK], D.loc[look_rows, 'pitch']), 150)
json.dump({'features': LOOK, 'classes': NB, 'trees': [flat(t) for t in ml.dump_model()['tree_info']], 'pitch': [flat(t) for t in mp.dump_model()['tree_info']]},
          open('/tmp/claude-0/plug/DonkAI/donk_look.json', 'w'), separators=(',', ':'))
mi.save_model('data/intent_v2.txt'); ml.save_model('data/look_v2.txt'); mp.save_model('data/pitch_v2.txt')
S = D[D.isdonk == 1].sample(300, random_state=3); pi = mi.predict(S[INT]); pl = ml.predict(S[LOOK]); pp = mp.predict(S[LOOK])
out = S[sorted(set(INT + LOOK))].astype(float)
for c in range(NS + 1): out[f'p{c}'] = pi[:, c]
for c in range(NB): out[f'l{c}'] = pl[:, c]
out['pp'] = pp; out.to_csv('/tmp/claude-0/plug/sample.csv', index=False)
print('EXPORTED', f'{time.time()-t0:.0f}s', flush=True)
