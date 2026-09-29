import numpy as np, pandas as pd, lightgbm as lgb, json, base64, re
from features import FEATS
from scipy.ndimage import binary_closing, binary_dilation, binary_erosion
D = pd.read_parquet('data/features.parquet'); D['is_scoped'] = D.is_scoped.astype(int)
ok = (D.frid2 == D.rid) & (D.falive2 == True)
P = dict(objective='huber', alpha=60, learning_rate=.08, num_leaves=31, min_data_in_leaf=100, feature_fraction=.8, bagging_fraction=.8, bagging_freq=1, verbose=-1, num_threads=4)
tr, te = ok & (D.match != 'falcons'), ok & (D.match == 'falcons') & (D.isdonk == 1)
mx = lgb.train(P, lgb.Dataset(D.loc[tr, FEATS], D.loc[tr, 'fX2']), 200); my = lgb.train(P, lgb.Dataset(D.loc[tr, FEATS], D.loc[tr, 'fY2']), 200)
E = D[te]; e = np.hypot(mx.predict(E[FEATS]) - E.fX2, my.predict(E[FEATS]) - E.fY2) * .0254
print('compact model holdout median m', round(float(np.median(e)), 2))
mx = lgb.train(P, lgb.Dataset(D.loc[ok, FEATS], D.loc[ok, 'fX2']), 200); my = lgb.train(P, lgb.Dataset(D.loc[ok, FEATS], D.loc[ok, 'fY2']), 200)
def flat(m):
    # every tree as parallel arrays; internal node ids >= 0, leaves encoded as ~leafIndex
    out = []
    for tr in m.dump_model()['tree_info']:
        feat, thr, left, right, dleft, leaf = [], [], [], [], [], []
        def walk(n):
            if 'leaf_value' in n: leaf.append(n['leaf_value']); return ~(len(leaf) - 1)
            i = len(feat); feat.append(n['split_feature']); thr.append(n['threshold']); dleft.append(1 if n.get('default_left') else 0); left.append(0); right.append(0)
            assert n['decision_type'] == '<='
            left[i] = walk(n['left_child']); right[i] = walk(n['right_child']); return i
        root = walk(tr['tree_structure'])
        out.append({'root': root, 'f': feat, 't': thr, 'l': left, 'r': right, 'd': dleft, 'v': leaf})
    return out
mx.save_model('data/gx.txt'); my.save_model('data/gy.txt')
json.dump({'features': FEATS, 'gx': flat(mx), 'gy': flat(my)}, open('/tmp/claude-0/plug/DonkAI/donk_model.json', 'w'), separators=(',', ':'))
# walkable grid (12 units / cell) from every alive position in the demos
xs, ys = [], []
for k in ['navi', 'aurora', '9z', 'g2', 'falcons']:
    t = pd.read_parquet(f'data/{k}_ticks.parquet', columns=['X', 'Y', 'is_alive', 'is_warmup_period']); t = t[t.is_alive & ~t.is_warmup_period]; xs.append(t.X.values); ys.append(t.Y.values)
X, Y = np.concatenate(xs), np.concatenate(ys); M = json.load(open('data/map.json')); S = 12
H, _, _ = np.histogram2d(Y, X, bins=[M['h'], M['w']], range=[[M['y0'], M['y0'] + M['h'] * S], [M['x0'], M['x0'] + M['w'] * S]])
walk = binary_closing(H >= 2, iterations=1)
safe = binary_erosion(walk, iterations=1)
bits = np.packbits(np.stack([walk, safe]).astype(np.uint8).ravel())
open('/tmp/claude-0/plug/DonkAI/Grid.cs', 'w').write(f'''namespace DonkAI;
// Walkable cells of de_dust2 learned from pro demo positions. Layer 0 = walkable, layer 1 = walkable with wall clearance.
public static class Grid {{
    public const double X0 = {M["x0"]!r}, Y0 = {M["y0"]!r}, Cell = {S};
    public const int W = {M["w"]}, H = {M["h"]};
    public static readonly byte[] Bits = System.Convert.FromBase64String("{base64.b64encode(bits.tobytes()).decode()}");
    public static bool Get(int layer, int cx, int cy) {{ if (cx < 0 || cy < 0 || cx >= W || cy >= H) return false; int i = layer * W * H + cy * W + cx; return (Bits[i >> 3] & (0x80 >> (i & 7))) != 0; }}
}}''')
open('/tmp/claude-0/plug/DonkAI/Features.cs', 'w').write('namespace DonkAI;\npublic static class FeatureNames { public static readonly string[] All = { ' + ', '.join(f'"{f}"' for f in FEATS) + ' }; }\n')
print('walkable cells', int(walk.sum()), 'safe', int(safe.sum()), FEATS)
