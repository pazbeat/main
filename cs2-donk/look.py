import pandas as pd, numpy as np, lightgbm as lgb, json, sys
LOOK = ['X', 'Y', 'Z', 'vx', 'vy', 'tr', 'team_num', 'health', 'wc', 'mates', 'enem', 'planted', 'ex', 'ey', 'ed', 'cx', 'cy', 'is_scoped', 'isdonk']
NB = 36
def prep(D):
    D = D[D.hok & D.yaw.notna()].copy(); D['is_scoped'] = D.is_scoped.astype(int)
    D['ybin'] = (((D.yaw + 360 + 180 / NB) % 360) // (360 / NB)).astype(int) % NB
    return D
def circ_err(pred_deg, true_deg): return np.abs((pred_deg - true_deg + 180) % 360 - 180)
P = dict(objective='multiclass', num_class=NB, learning_rate=.1, num_leaves=31, min_data_in_leaf=100, feature_fraction=.8, bagging_fraction=.7, bagging_freq=1, verbose=-1, num_threads=4)
PP = dict(objective='huber', alpha=5, learning_rate=.08, num_leaves=31, min_data_in_leaf=100, verbose=-1, num_threads=4)
def evaluate(D, donk_matches, rounds=120):
    r = {'model': [], 'move_dir': [], 'pitch_model': [], 'pitch_const': []}
    for test in donk_matches:
        tr, te = D.match != test, (D.match == test) & (D.isdonk == 1)
        m = lgb.train(P, lgb.Dataset(D.loc[tr, LOOK], D.loc[tr, 'ybin']), rounds)
        E = D[te]; pb = m.predict(E[LOOK]).argmax(1) * (360 / NB); pb = np.where(pb > 180, pb - 360, pb)
        e = circ_err(pb, E.yaw.values); mv = np.hypot(E.vx, E.vy) > 60
        md = np.degrees(np.arctan2(E.vy, E.vx)); em = np.where(mv, circ_err(md, E.yaw.values), np.nan)
        r['model'] += list(e); r['move_dir'] += list(em[mv])
        mp = lgb.train(PP, lgb.Dataset(D.loc[tr, LOOK], D.loc[tr, 'pitch']), 150)
        r['pitch_model'] += list(np.abs(mp.predict(E[LOOK]) - E.pitch)); r['pitch_const'] += list(np.abs(np.median(D.loc[tr, 'pitch']) - E.pitch))
        print(test, 'done', flush=True)
    return {'yaw_within15': round(float(np.mean(np.array(r['model']) <= 15)), 3), 'yaw_median_err': round(float(np.median(r['model'])), 1),
            'movedir_within15_when_moving': round(float(np.mean(np.array(r['move_dir']) <= 15)), 3), 'movedir_median_err': round(float(np.median(r['move_dir'])), 1),
            'pitch_mae_model': round(float(np.mean(r['pitch_model'])), 2), 'pitch_mae_const': round(float(np.mean(r['pitch_const'])), 2)}
if __name__ == '__main__':
    D = prep(pd.read_parquet('data/features.parquet'))
    print(json.dumps(evaluate(D, ['falcons', 'g2'] if 'quick' in sys.argv else ['navi', 'aurora', '9z', 'g2', 'falcons']), indent=1))
