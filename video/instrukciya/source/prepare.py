import json, sys, bisect
from PIL import Image, ImageChops, ImageStat

DEV = sys.argv[1]
FPS = 30
L = json.load(open('lines.json'))[DEV]
R = json.load(open(f'rec_{DEV}/log.json'))
VW, VH = R['viewport']['width'], R['viewport']['height']

# ---- screencast change detection (ignore frames identical to the previous one) ----
prev = None; changes = []
for fr in R['frames']:
    im = Image.open(fr['f']).convert('L').resize((96, int(96 * VH / VW)))
    if prev is None or ImageStat.Stat(ImageChops.difference(im, prev)).mean[0] > 0.35:
        changes.append(fr)
    prev = im
ct = [c['t'] for c in changes]
shots = sorted(R['shots'], key=lambda s: s['t']); st = [s['t'] for s in shots]
ptr = R['pointer']; pt = [p['t'] for p in ptr]
events = sorted(R['events'], key=lambda e: e['t'])
rec_lines = {x['id']: x for x in R['lines']}

def image_at(rt):
    i = bisect.bisect_right(ct, rt) - 1
    c = changes[max(i, 0)]
    j = bisect.bisect_right(st, rt) - 1
    if j >= 0 and shots[j]['t'] > c['t'] + 0.02:
        return shots[j]['f'], 1
    return c['f'], 0

def pointer_at(rt):
    i = bisect.bisect_right(pt, rt) - 1
    if i < 0: return None
    return ptr[i]['x'], ptr[i]['y']

# ---- build the global timeline ----
tl = []; T = 0.0; prev_kind = None; prev_sid = None
for ln in L:
    item = dict(sid=ln['sid'], kind=ln['kind'], id=ln['id'], cap=ln['cap'], wav=ln['wav'], vdur=ln['dur'], step=ln['extra'].get('step'))
    lead = 0.0
    if ln['sid'] != prev_sid: lead = 0.7 if ln['kind'] == 'g' else 0.35
    if ln['kind'] == 's':
        r = rec_lines[ln['id']]; item['r0'] = r['t0']; item['r1'] = r['t1']
        item['start'] = T + lead; item['voice'] = item['start']; item['end'] = item['start'] + (r['t1'] - r['t0'])
        if lead: item['r0'] -= lead   # hold the screen a moment before speaking
        item['start'] = T
    else:
        item['start'] = T; item['voice'] = T + lead + 0.1; item['end'] = item['voice'] + ln['dur'] + 0.55
    T = item['end']; tl.append(item); prev_sid = ln['sid']; prev_kind = ln['kind']
TOTAL = T + 1.2

# ---- per-frame plan ----
taps = [e['t'] for e in events if e['type'] in ('click', 'tap')]
NAV_T = taps[0] if DEV == 'pc' else taps[1]
def ease(x): return x * x * (3 - 2 * x)
frames = []
zs, zx, zy = 1.0, VW / 2, VH / 2   # smoothed zoom state (scale, centre in CSS px)
cur_focus = None
AREA_ASPECT = (VW, VH)
MAXZ = 1.45 if DEV == 'pc' else 1.25
for fi in range(int(TOTAL * FPS)):
    t = fi / FPS
    item = next((x for x in tl if x['start'] <= t < x['end']), tl[-1])
    fr = {'t': round(t, 3), 'sid': item['sid'], 'kind': item['kind'], 'lid': item['id']}
    if item['kind'] == 's':
        rt = item['r0'] + (t - item['start']) if 'r0' in item else item['r0']
        rt = min(rt, item['r1'])
        img, hi = image_at(rt); fr['img'] = img; fr['hi'] = hi
        pp = pointer_at(rt); fr['p'] = [round(pp[0], 1), round(pp[1], 1)] if pp else None
        fr['clicks'] = [[round(e['x'], 1), round(e['y'], 1), round(rt - e['t'], 3), e['type']] for e in events if e['type'] in ('click', 'tap') and 0 <= rt - e['t'] < .7]
        fr['swipes'] = [[e['x0'], e['y0'], e['x1'], e['y1'], round((rt - e['t']) / (e['ms'] / 1000), 3)] for e in events if e['type'] == 'swipe' and -0.1 <= rt - e['t'] < e['ms'] / 1000 + .35]
        fr['rings'] = [[round(e['x'], 1), round(e['y'], 1), round(e['w'], 1), round(e['h'], 1), round(rt - e['t'], 3)] for e in events if e['type'] == 'ring' and 0 <= rt - e['t'] < 2.6]
        # zoom target from the latest focus/unfocus event
        fe = [e for e in events if e['type'] in ('focus', 'unfocus') and e['t'] <= rt]
        target = (1.0, VW / 2, VH / 2)
        if fe and fe[-1]['type'] == 'focus':
            e = fe[-1]; s = min(MAXZ, VW * .82 / max(e['w'], 1), VH * .82 / max(e['h'], 1)); s = max(1.0, s)
            cx, cy = e['x'] + e['w'] / 2, e['y'] + e['h'] / 2
            cx = min(max(cx, VW / (2 * s)), VW - VW / (2 * s)); cy = min(max(cy, VH / (2 * s)), VH - VH / (2 * s))
            target = (s, cx, cy)
        k = 1 - pow(0.001, 1 / (FPS * 0.9))   # ~0.9 s settle
        zs += (target[0] - zs) * k; zx += (target[1] - zx) * k; zy += (target[2] - zy) * k
        fr['z'] = [round(zs, 4), round(zx, 2), round(zy, 2)]
        fr['url'] = 'imbir.kz/ru' if rt < NAV_T + .4 else 'imbir.kz/ru/create'
    else:
        zs, zx, zy = 1.0, VW / 2, VH / 2
    # captions: show while the line is spoken (+ a little)
    capi = next((x for x in tl if x['voice'] - .05 <= t < x['voice'] + x['vdur'] + .45), None)
    fr['cap'] = capi['cap'] if capi else ''
    fr['step'] = item['step']
    frames.append(fr)

json.dump({'dev': DEV, 'fps': FPS, 'vw': VW, 'vh': VH, 'total': TOTAL, 'lines': tl, 'frames': frames}, open(f'plan_{DEV}.json', 'w'), ensure_ascii=False)
print(DEV, 'duration', round(TOTAL, 1), 's', len(frames), 'frames', 'changes', len(changes), 'shots', len(shots))
