import numpy as np, pandas as pd, json
from scen_data import load, zone, group
A, B = np.array([1111, 2551]), np.array([-1503, 2524])
# ---------- real references ----------
ref = {}
Dd = load(['isdonk', 'team_num', 'tr', 'X', 'Y', 'rid', 'planted', 'name'], donk_only=True); Dd = Dd[Dd.isdonk == 1]
for team, key in ((2, 'T'), (3, 'CT')):
    r = Dd[(Dd.team_num == team) & Dd.tr.between(19.5, 20.5)].groupby(['match', 'rid']).head(1)
    ref[f'start_{key}'] = pd.Series(group(zone(r.X.values, r.Y.values))).value_counts(normalize=True).round(3).to_dict()
Da = load(['team_num', 'tr', 'X', 'Y', 'rid', 'planted', 'name', 'tick'])
P = Da[(Da.planted == 1) & Da.bx.notna()].copy(); P['t_since'] = (P.tick - P.btick) / 64; P['bd'] = np.hypot(P.X - P.bx, P.Y - P.by)
ct = P[P.team_num == 3].sort_values('t_since'); g = ct.groupby(['match', 'rid', 'name'])
first = g.head(1).set_index(['match', 'rid', 'name']); last20 = ct[ct.t_since <= 20].groupby(['match', 'rid', 'name']).tail(1).set_index(['match', 'rid', 'name'])
j = first[['bd']].join(last20[['bd']], rsuffix='_20'); j = j[j.bd >= 1500]
ref['retake_halved_20s'] = round(float((j.bd_20 <= 0.5 * j.bd).mean()), 3)
t = P[(P.team_num == 2) & (P.t_since <= 25)]; st = t.sort_values('t_since').groupby(['match', 'rid', 'name']).head(1)
near = st[st.bd < 1000].set_index(['match', 'rid', 'name']).index
tt = t.set_index(['match', 'rid', 'name']).loc[lambda x: x.index.isin(near)]
ref['postplant_within1200'] = round(float((tt.bd < 1200).mean()), 3)
for site_name, sxy in (('A', (1111, 2551)), ('B', (-1503, 2524))):
    q = tt.reset_index(); q = q[(np.hypot(q.bx - sxy[0], q.by - sxy[1]) < 600) & (q.t_since <= 25)]
    ref[f'postplant_zones_{site_name}'] = pd.Series(zone(q.X.values, q.Y.values)).value_counts(normalize=True).round(3).to_dict()
j2 = first[['bd']].join(last20[['bd']], rsuffix='_20')
nr = j2[(j2.bd >= 500) & (j2.bd < 1500)]; ref['near_ct_rel20'] = round(float(((nr.bd - nr.bd_20) / nr.bd).mean()), 3)
fr = j2[j2.bd >= 1500]; ref['far_ct_rel20'] = round(float(((fr.bd - fr.bd_20) / fr.bd).mean()), 3)
print('real refs', ref, flush=True)
# ---------- bench ----------
def analyze(path):
    T = pd.read_csv(path); res = []
    def runs(name): return T[T.scenario == name]
    def end(name):
        return runs(name).groupby('seed').tail(1)
    def add(name, metric, value, ref_value, ok, note=''):
        res.append({'scenario': name, 'metric': metric, 'bot': value, 'reference': ref_value, 'pass': bool(ok), 'note': note})
    for key, name in (('T', 'T: старт раунда'), ('CT', 'CT: старт раунда')):
        e = runs(name); e = e[(e.t - e.t.min()).between(19.9, 20.3)].groupby('seed').head(1)
        dist = pd.Series(group(zone(e.x.values, e.y.values))).value_counts(normalize=True).round(3).to_dict(); r = ref[f'start_{key}']
        tv = 0.5 * sum(abs(dist.get(k, 0) - r.get(k, 0)) for k in set(dist) | set(r)); top = max(r, key=r.get)
        add(name, 'где через 20 с (доли по зонам)', dist, r, tv <= 0.5 and dist.get(top, 0) >= 0.2, f'расхождение {tv:.2f}; главное направление donk: {top}')
    def dchange(name, site):
        e = runs(name); s0 = e.groupby('seed').head(1).set_index('seed'); f = e.groupby('seed').tail(1).set_index('seed')
        d0 = np.hypot(s0.x - site[0], s0.y - site[1]); d1 = np.hypot(f.x - site[0], f.y - site[1]); return float(((d0 - d1) / d0).mean()), float((d1 - d0).mean())
    for name, site in (('CT: бомба на A, бот рядом (5–15 м)', A), ('CT: бомба на B, бот рядом (5–15 м)', B)):
        rel, _ = dchange(name, site); add(name, 'на сколько сократил расстояние до бомбы за 20 с', f'{rel*100:.0f}%', f"реальные CT: {ref['near_ct_rel20']*100:.0f}%", rel >= 0.5 * ref['near_ct_rel20'])
    rel, _ = dchange('CT: бомба на A, бот далеко на B', A)
    add('CT: бомба на A, бот далеко на B', 'не бросается через всю карту (сокращение за 20 с)', f'{rel*100:.0f}%', f"реальные CT: {ref['far_ct_rel20']*100:.0f}% (сохраняют оружие)", rel <= max(0.3, ref['far_ct_rel20'] + 0.2))
    _, dd = dchange('T: скоро взрыв, бот у бомбы на A', A)
    add('T: скоро взрыв, бот у бомбы на A', 'отошёл от бомбы за 10 с (м)', round(dd * .0254, 1), '> 0 (реальные T убегают от взрыва)', dd > 100)
    _, dd = dchange('CT: скоро взрыв, бот в 5–15 м от бомбы', A)
    add('CT: скоро взрыв, бот в 5–15 м от бомбы', 'не лезет к бомбе за 10 с до взрыва (м)', round(dd * .0254, 1), '≥ 0 (реальные CT отходят)', dd > -100)
    for name, key in (('T: после закладки на A', 'A'), ('T: после закладки на B', 'B')):
        e = runs(name); dist = pd.Series(zone(e.x.values, e.y.values)).value_counts(normalize=True); r = ref[f'postplant_zones_{key}']
        tv = 0.5 * sum(abs(dist.get(k, 0) - r.get(k, 0)) for k in set(dist.index) | set(r)); top = {k: round(float(v), 2) for k, v in dist.head(4).items()}
        far = [z for z in dist.index if r.get(z, 0) < 0.03]; fb = float(dist[far].sum()); fr = float(sum(v for k, v in r.items() if v < 0.03))
        add(name, 'где держит позицию (зоны за 25 с)', top, {k: round(v, 2) for k, v in list(r.items())[:4]}, tv <= 0.5 and fb <= max(0.1, 2 * fr), f'расхождение {tv:.2f}; в редких для профи зонах {fb:.0%} (у профи {fr:.0%})')
    def end_dist(name, p):
        f = end(name); return float(np.hypot(f.x - p[0], f.y - p[1]).mean())
    Bp = (-1700, 1300)
    a, c = end_dist('CT: враги на B, бот на A', Bp), end_dist('CT: бот на A, врагов не видно (контроль)', Bp)
    add('CT: враги на B, бот на A', 'сместился к B сильнее, чем без врагов (м)', round((c - a) * .0254, 1), '> 0', c - a > 100, f'в конце до B: {a*.0254:.0f} м против {c*.0254:.0f} м в контроле')
    def to_site(f): return np.minimum(np.hypot(f.x - A[0], f.y - A[1]), np.hypot(f.x - B[0], f.y - B[1])).mean()
    a, c = to_site(end('T: 1:25 раунда, бомба не заложена')), to_site(end('T: 0:20 раунда (контроль)'))
    add('T: 1:25 раунда, бомба не заложена', 'ближе к сайту, чем в начале раунда (м)', round((c - a) * .0254, 1), '≥ 0 (реальные игроки почти не меняются)', c - a > -100, f'до ближайшего сайта: {a*.0254:.0f} м против {c*.0254:.0f} м')
    E = (1300, 1150); a, c = end_dist('T: враг рядом на длинном', E), end_dist('T: на длинном без врага (контроль)', E)
    add('T: враг рядом на длинном', 'сблизился с врагом сильнее, чем без врага (м)', round((c - a) * .0254, 1), '> 0 (реальные игроки идут на контакт)', c - a > 50, f'в конце до врага: {a*.0254:.0f} м против {c*.0254:.0f} м')
    h1 = float((runs('T: клатч 1 против 3')['mode'] == 'hold').mean()); h0 = float((runs('T: те же точки, вся команда жива (контроль)')['mode'] == 'hold').mean())
    add('T: клатч 1 против 3', 'доля «стоять» (клатч / вся команда)', f'{h1:.2f} / {h0:.2f}', 'реальные: 0.40 / 0.47', h1 < h0)
    R = T[T.scenario.str.startswith('random_')]
    per = R.groupby('scenario').agg(n=('t', 'size'), stuck=('stuck', 'sum'), hold=('mode', lambda s: (s == 'hold').mean()), x0=('x', 'first'), y0=('y', 'first'), x1=('x', 'last'), y1=('y', 'last'))
    moved = np.hypot(per.x1 - per.x0, per.y1 - per.y0)
    frozen_move = R.groupby('scenario').apply(lambda g: bool(((g['mode'] == 'move').mean() > .5) and np.hypot(g.x.iloc[-1] - g.x.iloc[0], g.y.iloc[-1] - g.y.iloc[0]) < 100))
    def reversals(g):                     # real movement heading, 1 s steps, only while actually moving
        x, y = g.x.values[::8], g.y.values[::8]; dx, dy = np.diff(x), np.diff(y); mv = np.hypot(dx, dy) > 60
        h = np.degrees(np.arctan2(dy, dx))[mv]; return int((np.abs((np.diff(h) + 180) % 360 - 180) > 150).sum()) if len(h) > 1 else 0
    rev = R.groupby('scenario').apply(reversals)
    add('Надёжность: 300 случайных стартов', 'застреваний на проверку', round(float(per.stuck.sum() / (per.n.sum() / 6)), 3), '< 0.05', per.stuck.sum() / (per.n.sum() / 6) < 0.05)
    add('Надёжность: 300 случайных стартов', 'прогонов «хочет идти, но стоит на месте»', round(float(frozen_move.mean()), 3), '< 0.05', frozen_move.mean() < 0.05)
    add('Надёжность: 300 случайных стартов', 'резких разворотов на 180° за 30 с (в среднем)', round(float(rev.mean()), 2), 'реальные игроки: 1.46 → порог ≤ 2.2', rev.mean() <= 1.5 * 1.46)
    add('Надёжность: 300 случайных стартов', 'доля времени «стоять»', round(float(per.hold.mean()), 2), 'донк ≈ 0.45–0.5', 0.25 <= per.hold.mean() <= 0.7)
    return res
import sys
runs_ = [(a.split('=')[0], a.split('=')[1]) for a in sys.argv[1:]] or [('v0.2', '/tmp/claude-0/plug/trace_v02.csv'), ('v0.3', '/tmp/claude-0/plug/trace_v03.csv')]
out = {'reference': ref}
for k, pth in runs_: out[k] = analyze(pth)
json.dump(out, open('data/scen_results.json', 'w'), ensure_ascii=False, indent=1, default=str)
for v in [k for k in out if k != 'reference']:
    print(f'== {v}: {sum(r["pass"] for r in out[v])} of {len(out[v])} passed')
    for r in out[v]: print(' ', 'OK ' if r['pass'] else 'FAIL', r['scenario'], '|', r['metric'], '|', r['bot'], '| ref', r['reference'], '|', r['note'])
