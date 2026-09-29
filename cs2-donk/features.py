import numpy as np, pandas as pd
MATCHES = ['navi', 'aurora', '9z', 'g2', 'falcons']
HZ = 16
def wclass(w):
    w = str(w)
    if w in ('AWP', 'SSG 08'): return 1
    if w in ('AK-47', 'M4A4', 'M4A1-S', 'Galil AR', 'FAMAS', 'AUG', 'SG 553'): return 2
    if w in ('MAC-10', 'MP9', 'MP7', 'UMP-45', 'P90', 'PP-Bizon', 'MP5-SD'): return 3
    if w in ('Desert Eagle', 'Glock-18', 'USP-S', 'P2000', 'P250', 'Five-SeveN', 'Tec-9', 'CZ75-Auto', 'Dual Berettas', 'R8 Revolver'): return 4
    if 'Grenade' in w or w in ('Flashbang', 'Molotov', 'Incendiary Grenade', 'Decoy Grenade'): return 5
    if w in ('C4 Explosive',): return 6
    return 0  # knife / other
def wrap(a): return (a + 180) % 360 - 180
def build(k):
    t = pd.read_parquet(f'data/{k}_ticks.parquet')
    t = t[(~t.is_warmup_period) & (~t.is_freeze_period)].copy()
    fe = pd.read_parquet(f'data/{k}_round_freeze_end.parquet').tick.sort_values().values
    t['rstart'] = fe[np.clip(np.searchsorted(fe, t.tick.values, side='right') - 1, 0, None)]
    t['tr'] = (t.tick - t.rstart) / 64.0
    t['rid'] = np.searchsorted(fe, t.tick.values, side='right')
    try:
        bp = pd.read_parquet(f'data/{k}_bomb_planted.parquet')[['tick']].sort_values('tick').values[:, 0]
    except Exception: bp = np.array([])
    t = t.sort_values(['steamid', 'tick']).reset_index(drop=True)
    g = t.groupby('steamid', sort=False)
    # history (memory) and future targets, per player; valid only inside same round & alive
    for lag, nm in [(4, '0_25'), (8, '0_5'), (16, '1'), (32, '2')]:
        for c in ('X', 'Y'):
            t[f'h{c}{nm}'] = t[c] - g[c].shift(lag)
    t['vx'], t['vy'] = t.hX0_25 * 4, t.hY0_25 * 4
    t['hyaw0_25'] = wrap(t.yaw - g.yaw.shift(4))
    for lead, nm in [(16, '1'), (32, '2')]:
        for c in ('X', 'Y'): t[f'f{c}{nm}'] = g[c].shift(-lead) - t[c]
        t[f'frid{nm}'] = g.rid.shift(-lead); t[f'falive{nm}'] = g.is_alive.shift(-lead)
    t['fyaw0_5'] = wrap(g.yaw.shift(-8) - t.yaw); t['fpitch0_5'] = g.pitch.shift(-8) - t.pitch
    t['ffire'] = sum(g.FIRE.shift(-i).fillna(False).astype(int) for i in range(1, 5)).clip(0, 1)
    t['hrid'] = g.rid.shift(32)
    t['ysin'], t['ycos'] = np.sin(np.radians(t.yaw)), np.cos(np.radians(t.yaw))
    t['wc'] = t.active_weapon_name.map(wclass)
    # team context per tick
    alive = t[t.is_alive]
    cnt = alive.groupby(['tick', 'team_num']).size().rename('n').reset_index()
    t = t.merge(cnt.rename(columns={'n': 'm_n'}), on=['tick', 'team_num'], how='left')
    t = t.merge(cnt.assign(team_num=5 - cnt.team_num).rename(columns={'n': 'enem'}), on=['tick', 'team_num'], how='left')
    t['mates'] = t.m_n.fillna(1) - t.is_alive.astype(int); t['enem'] = t.enem.fillna(0)
    if len(bp):
        last = bp[np.clip(np.searchsorted(bp, t.tick.values, side='right') - 1, 0, None)]
        t['planted'] = ((last <= t.tick.values) & (last >= t.rstart.values)).astype(int)
    else: t['planted'] = 0
    t['row'] = np.arange(len(t))
    e = alive[alive.spotted][['tick', 'team_num', 'X', 'Y']].rename(columns={'team_num': 'et', 'X': 'EX', 'Y': 'EY'})
    m = t[['row', 'tick', 'team_num', 'X', 'Y']].merge(e, on='tick'); m = m[m.et != m.team_num]
    m['dd'] = np.hypot(m.EX - m.X, m.EY - m.Y); m = m.sort_values('dd').drop_duplicates('row')
    t['ex'] = 0.0; t['ey'] = 0.0; t['ed'] = 4000.0
    t.loc[m.row.values, 'ex'] = (m.EX - m.X).values; t.loc[m.row.values, 'ey'] = (m.EY - m.Y).values; t.loc[m.row.values, 'ed'] = m.dd.values
    c = alive.groupby(['tick', 'team_num'])[['X', 'Y']].mean().rename(columns={'X': 'CX', 'Y': 'CY'}).reset_index()
    t = t.merge(c, on=['tick', 'team_num'], how='left'); t['cx'] = (t.CX - t.X).fillna(0); t['cy'] = (t.CY - t.Y).fillna(0)
    t['eang'] = np.where(t.ed < 4000, wrap(np.degrees(np.arctan2(t.ey, t.ex)) - t.yaw), 0)
    t['match'] = k
    t = t[t.is_alive & (t.hrid == t.rid)]
    return t
FEATS = ['X', 'Y', 'Z', 'vx', 'vy', 'ysin', 'ycos', 'pitch', 'hX0_5', 'hY0_5', 'hX1', 'hY1', 'hX2', 'hY2', 'hyaw0_25', 'tr', 'team_num', 'health', 'armor_value', 'wc', 'mates', 'enem', 'planted', 'ex', 'ey', 'ed', 'eang', 'cx', 'cy', 'is_scoped', 'isdonk']
if __name__ == '__main__':
    import sys
    parts = []
    for k in MATCHES:
        d = build(k); d['isdonk'] = (d.name == 'donk').astype(int); parts.append(d); print(k, len(d), flush=True)
    pd.concat(parts).to_parquet('data/features.parquet')
