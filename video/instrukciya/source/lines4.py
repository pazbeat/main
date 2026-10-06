import json, sys
from script_v4 import flow
LANG = sys.argv[1]; D = json.load(open(f'el/{LANG}_dur.json'))
out = {}
for dev in ['pc', 'mob']:
    out[dev] = [{'sid': sid, 'kind': kind, 'id': lid, 'cap': cap, 'act': act or '', 'extra': extra, 'wav': f'el/{LANG}_{lid}.wav', 'dur': D[lid]}
                for sid, kind, lines in flow(LANG) for lid, cap, act, extra in lines]
json.dump(out, open(f'lines4_{LANG}.json', 'w'), ensure_ascii=False, indent=1)
print(LANG, round(sum(x['dur'] for x in out['pc']), 1), 's speech')
