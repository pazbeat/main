# Factor tests. For real situations that contain a factor (enemy close, bomb down, clock running out, ...)
#  - real effect  = players in that situation vs players in the same zone / side / round-time bucket without it
#  - model effect = model on those situations vs the same situations with only that factor removed
# PASS when the model moves the same way as real players and at least a quarter as much.
import numpy as np, pandas as pd, lightgbm as lgb, json, sys
from scen_data import load, zone
from intent import label
model_file = sys.argv[1] if len(sys.argv) > 1 else 'data/intent_v2b.txt'
m = lgb.Booster(model_file=model_file); F = m.feature_name()
cols = list(dict.fromkeys([f for f in F if f not in ('bdx', 'bdy', 'bd', 'bang', 'tp')] + ['fX2', 'fY2', 'frid2', 'falive2', 'rid', 'isdonk', 'team_num', 'tr', 'planted', 'tick', 'health', 'mates', 'ed', 'ex', 'ey', 'X', 'Y', 'cx', 'cy', 'eang']))
D = load(cols); D['is_scoped'] = D.is_scoped.astype(int)
D = D[(D.frid2 == D.rid) & (D.falive2 == True)].copy()
D['cls'] = label(D.fX2.values, D.fY2.values)
D['zone'] = zone(D.X.values, D.Y.values); D['tb'] = (D.tr // 15).clip(0, 8)
def bomb_feats(X):
    X['bdx'] = np.where(X.planted == 1, X.bx - X.X, 0); X['bdy'] = np.where(X.planted == 1, X.by - X.Y, 0); X['bd'] = np.where(X.planted == 1, np.hypot(X.bdx, X.bdy), 4000); X['bang'] = np.where(X.planted == 1, np.degrees(np.arctan2(X.bdy, X.bdx)), -999); X['tp'] = np.where((X.planted == 1) & X.btick.notna(), (X.tick - X.btick) / 64, -1); return X
D = bomb_feats(D)
rng = np.random.default_rng(0); ANG = np.radians((np.arange(9) - 1) * 45.0)
L = np.hypot(D.fX2, D.fY2).values + 1e-9; D['rux'] = D.fX2 / L; D['ruy'] = D.fY2 / L; D.loc[D.cls == 0, ['rux', 'ruy']] = 0
def mstats(X):
    p = m.predict(X[F]); return p[:, 0], (p[:, 1:] * np.cos(ANG[1:])).sum(1), (p[:, 1:] * np.sin(ANG[1:])).sum(1)
def tow(ux, uy, tx, ty): return (ux * tx + uy * ty) / (np.hypot(tx, ty) + 1e-9)
def matched(S, pool, metric):
    """real effect: metric(S) - metric(pool) inside the same (team, zone, time bucket), weighted by S."""
    a = S.assign(v=metric(S)).groupby(['team_num', 'zone', 'tb']).v.agg(['mean', 'size']); b = pool.assign(v=metric(pool)).groupby(['team_num', 'zone', 'tb']).v.mean()
    j = a.join(b.rename('base'), how='inner'); j = j[j['size'] >= 30]; return float((j['mean'] * j['size']).sum() / j['size'].sum()), float((j['base'] * j['size']).sum() / j['size'].sum())
def sample(mask, n=40000):
    idx = np.flatnonzero(mask.values); return D.iloc[rng.choice(idx, min(n, len(idx)), replace=False)].copy()
out = []
def report(name, what, real_with, real_without, model_with, model_without):
    re, me = real_with - real_without, model_with - model_without
    # same direction and at least a quarter of the real effect; if real players barely react (<0.03), the model should barely react too
    ok = bool((np.sign(re) == np.sign(me) and abs(me) >= 0.25 * abs(re)) or (abs(re) < 0.03 and abs(me) < 0.03))
    out.append({'test': name, 'what': what, 'real_without': round(float(real_without), 3), 'real_with': round(float(real_with), 3), 'model_without': round(float(model_without), 3), 'model_with': round(float(model_with), 3), 'pass': ok}); print(out[-1], flush=True)
hold = lambda X: (X.cls == 0).astype(float).values
# 1) enemy seen close (by the team)
S = sample((D.ed < 800) & (D.tr > 5)); pool = D[(D.ed >= 3999) & (D.tr > 5)]
rw, rb = matched(S, pool, hold); A = S.copy(); A[['ex', 'ey']] = 0; A['ed'] = 4000; A['eang'] = 0
report('Враг рядом (виден команде)', 'доля «стоять»', rw, rb, mstats(S)[0].mean(), mstats(A)[0].mean())
# 1b) ... and does the player turn toward / away from it
towE = lambda X: tow(X.rux.values, X.ruy.values, X.ex.values, X.ey.values)
rw = towE(S).mean(); _, ux, uy = mstats(S); mw = tow(ux, uy, S.ex.values, S.ey.values).mean(); _, ux, uy = mstats(A); mb = tow(ux, uy, S.ex.values, S.ey.values).mean()
rb = 0.0
report('Враг рядом: идти к нему или от него', 'движение к врагу (−1…1)', rw, rb, mw, mb)
# 2) low HP
S = sample((D.health <= 35) & (D.tr > 5)); pool = D[(D.health >= 90) & (D.tr > 5)]
rw, rb = matched(S, pool, hold); A = S.copy(); A['health'] = 100
report('Мало HP', 'доля «стоять»', rw, rb, mstats(S)[0].mean(), mstats(A)[0].mean())
# 3) last alive
S = sample((D.mates == 0) & (D.tr > 10)); pool = D[(D.mates >= 3) & (D.tr > 10)]
rw, rb = matched(S, pool, hold); A = S.copy(); A['mates'] = 4
report('Остался один (клатч)', 'доля «стоять»', rw, rb, mstats(S)[0].mean(), mstats(A)[0].mean())
# 4) CT, bomb down -> toward the bomb
S = sample((D.team_num == 3) & (D.planted == 1) & D.bx.notna())
pool = D[(D.team_num == 3) & (D.planted == 0) & (D.tr > 20)].copy()
pool['bx'] = np.where(np.hypot(pool.X - 1129, pool.Y - 2599) < np.hypot(pool.X + 1684, pool.Y - 2408), 1129, -1684); pool['by'] = np.where(pool.bx > 0, 2599, 2408)
towB = lambda X: tow(X.rux.values, X.ruy.values, (X.bx - X.X).values, (X.by - X.Y).values)
rw, rb = matched(S, pool, towB); A = S.copy(); A['planted'] = 0; A = bomb_feats(A)
_, ux, uy = mstats(S); mw = tow(ux, uy, (S.bx - S.X).values, (S.by - S.Y).values).mean(); _, ux, uy = mstats(A); mb = tow(ux, uy, (S.bx - S.X).values, (S.by - S.Y).values).mean()
report('CT: бомба заложена → ретейк', 'движение к бомбе (−1…1)', rw, rb, mw, mb)
# 5) T, bomb down -> hold around it
S = sample((D.team_num == 2) & (D.planted == 1) & D.bx.notna()); pool = D[(D.team_num == 2) & (D.planted == 0) & (D.tr > 20)]
rw, rb = matched(S, pool, hold); A = S.copy(); A['planted'] = 0; A = bomb_feats(A)
report('T: после закладки держит позицию', 'доля «стоять»', rw, rb, mstats(S)[0].mean(), mstats(A)[0].mean())
# 6) T, clock running out, no plant -> go to a site
def to_site(X, ux, uy):
    dA = np.hypot(1129 - X.X, 2599 - X.Y); dB = np.hypot(-1684 - X.X, 2408 - X.Y)
    return tow(ux, uy, np.where(dA < dB, 1129 - X.X, -1684 - X.X), np.where(dA < dB, 2599 - X.Y, 2408 - X.Y))
S = sample((D.team_num == 2) & (D.planted == 0) & (D.tr > 70)); pool = D[(D.team_num == 2) & (D.planted == 0) & D.tr.between(15, 45)]
S2, pool2 = S.assign(tb=0), pool.assign(tb=0)      # compare by zone only: time is the factor under test
rw, rb = matched(S2, pool2, lambda X: to_site(X, X.rux.values, X.ruy.values)); A = S.copy(); A['tr'] = 30
_, ux, uy = mstats(S); mw = to_site(S, ux, uy).mean(); _, ux, uy = mstats(A); mb = to_site(S, ux, uy).mean()
report('T: мало времени, бомба не заложена', 'движение к ближайшему сайту', rw, rb, mw, mb)
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else 'data/factor_tests.json', 'w'), ensure_ascii=False, indent=1)
print('PASSED', sum(o['pass'] for o in out), 'of', len(out))
