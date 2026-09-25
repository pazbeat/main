import json, sys
DEV = sys.argv[1]; FPS = 30
L = json.load(open('lines.json'))[DEV]
M = json.load(open(f'rec2_{DEV}/meta.json'))
VW, VH = M['viewport']['width'], M['viewport']['height']
MAXZ = 1.32 if DEV == 'pc' else 1.0
NF = len(M['frames']); fpath = lambda i: f"rec2_{DEV}/f/{min(max(i, 0), NF - 1):06d}.jpg"
rl = {x['id']: x for x in M['lines']}
DIFF = json.load(open(f'rec2_{DEV}/diffs.json'))

# ---- timeline ----
tl = []; T = 0.0; prev_sid = None
for ln in L:
    it = dict(sid=ln['sid'], kind=ln['kind'], id=ln['id'], cap=ln['cap'], wav=ln['wav'], vdur=ln['dur'], step=ln['extra'].get('step'))
    lead = (0.5 if ln['kind'] == 'g' else 0.35) if ln['sid'] != prev_sid else 0.0
    it['start'] = T
    if ln['kind'] == 's':
        r = rl[ln['id']]; f0 = r['f0']; f1 = r['f1']
        # trim the static tail: keep everything up to the last activity, and at least the (new, shorter) voice
        last = f0
        for f in range(f0, f1):
            fr = M['frames'][f]
            moved = f > f0 and fr['p'] != M['frames'][f - 1]['p']
            if DIFF[f] > 0.25 or fr['fx'] or moved: last = f
        for c in M['cams']:
            if f0 <= c['f'] < f1: last = max(last, min(f1 - 1, c['f'] + 32))
        f1 = min(f1, max(last + 8, f0 + int((ln['dur'] + 0.3) * FPS + .999)))
        it['f0'] = f0; it['f1'] = f1; it['lead'] = lead
        it['voice'] = T + lead; it['end'] = it['voice'] + (r['f1'] - r['f0']) / FPS
    else:
        it['voice'] = T + lead + 0.05; it['end'] = it['voice'] + ln['dur'] + 0.35
    T = it['end']; tl.append(it); prev_sid = ln['sid']
TOTAL = T + 1.5

# ---- camera track over recorded frames (eased transitions between framed rects) ----
def target(r):
    if r is None: return (1.0, VW / 2, VH / 2)
    x, y, w, h = r; s = max(1.0, min(MAXZ, VW / w, VH / h))
    cx, cy = x + w / 2, y + h / 2
    hw, hh = VW / (2 * s), VH / (2 * s)
    return (s, min(max(cx, hw), VW - hw), min(max(cy, hh), VH - hh))
cams = sorted(M['cams'], key=lambda c: c['f'])
def ease(k): return 4 * k ** 3 if k < .5 else 1 - (-2 * k + 2) ** 3 / 2
cam_track = []; state = (1.0, VW / 2, VH / 2); frm = state; to = state; t0 = 0; TR = 30   # 1.0 s transitions
ci = 0
for f in range(NF):
    while ci < len(cams) and cams[ci]['f'] <= f:
        cur = cam_track[-1] if cam_track else state
        frm = cur; to = target(cams[ci]['r']); t0 = cams[ci]['f']; ci += 1
    k = ease(min(1, (f - t0) / TR)) if f >= t0 else 1
    cam_track.append(tuple(a + (b - a) * k for a, b in zip(frm, to)))

# ---- effect events with frame indices ----
ev = []
for f, fr in enumerate(M['frames']):
    for e in fr['fx']: ev.append((f, e))

# hard cuts inside the recording (page load, modal closing): hold the outgoing frame, then crossfade
J = [j for j, d in json.load(open(f'rec2_{DEV}/jumps.json')) if d > 40]
groups = []
for j in J:
    if groups and j - groups[-1][1] <= 6: groups[-1][1] = j
    else: groups.append([j, j])
def blend_for(f):
    for a, bnd in groups:
        if a <= f < bnd + 10:
            return fpath(a - 1), round(1 - min(1, max(0, (f - bnd) / 10)) ** 1 if f >= bnd else 1, 3)
    return None, 0
def rec_state(f):
    fr = M['frames'][min(f, NF - 1)]
    clicks = [[e[1], e[2], round((f - g) / FPS, 3), e[0]] for g, e in ev if e[0] in ('click', 'tap') and 0 <= f - g < 20]
    rings = [[e[1], e[2], e[3], e[4], round((f - g) / FPS, 3)] for g, e in ev if e[0] == 'ring' and 0 <= f - g < 80]
    touch = [[e[1], e[2]] for g, e in ev if e[0] == 'touch' and g == f]
    z = cam_track[min(f, NF - 1)]
    bi, ba = blend_for(f)
    return {'img': fpath(f), 'bimg': bi, 'ba': ba, 'p': fr['p'], 'clicks': clicks, 'rings': rings, 'touch': touch, 'z': [round(z[0], 4), round(z[1], 2), round(z[2], 2)]}

frames = []
first_click = next((g for g, e in ev if e[0] in ('click', 'tap')), 10 ** 9)
nav = first_click if DEV == 'pc' else next((g for g, e in ev[1:] if e[0] in ('click', 'tap') and g > first_click), 10 ** 9)
XF = 0.6
for fi in range(int(TOTAL * FPS)):
    t = fi / FPS
    it = next((x for x in tl if x['start'] <= t < x['end']), tl[-1])
    fr = {'t': round(t, 3), 'sid': it['sid'], 'kind': it['kind'], 'step': it['step']}
    if it['kind'] == 's':
        f = it['f0'] + max(0, round((t - it['voice']) * FPS)) if t >= it['voice'] else it['f0']
        f = min(f, it['f1']); fr.update(rec_state(f)); fr['url'] = 'imbir.kz/ru' if f < nav + 10 else 'imbir.kz/ru/create'
    # crossfade with the previous scene of a different kind
    k = tl.index(it)
    if k > 0 and tl[k - 1]['kind'] != it['kind'] and t - it['start'] < XF:
        pv = tl[k - 1]; fr['xa'] = round(ease((t - it['start']) / XF), 3); fr['xsid'] = pv['sid']; fr['xkind'] = pv['kind']
        if pv['kind'] == 's': fr['x'] = rec_state(pv['f1'])
        else: fr['xt'] = round(pv['end'] - 0.001, 3)
    # captions with soft fades
    c = next((x for x in tl if x['voice'] - .1 <= t < x['voice'] + x['vdur'] + .5), None)
    if c:
        a = min(1, (t - (c['voice'] - .1)) / .2, (c['voice'] + c['vdur'] + .5 - t) / .25); fr['cap'] = c['cap']; fr['ca'] = round(max(0, a), 3)
    else: fr['cap'] = ''; fr['ca'] = 0
    frames.append(fr)

json.dump({'dev': DEV, 'fps': FPS, 'vw': VW, 'vh': VH, 'total': TOTAL, 'lines': tl, 'frames': frames}, open(f'plan2_{DEV}.json', 'w'), ensure_ascii=False)
print(DEV, 'duration', round(TOTAL, 1), 'rec frames', NF)
