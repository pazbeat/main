import sys, os, subprocess, pandas as pd
from demoparser2 import DemoParser
B = "https://huggingface.co/datasets/cs2povarchive/cs2-demos/resolve/main/iem_cologne_major_2026/"
DEMOS = {"navi": "2394900-natus-vincere-vs-spirit-iem-cologne-major/natus-vincere-vs-spirit-m1-dust2.dem",
         "aurora": "2394977-aurora-vs-spirit-iem-cologne-major/aurora-vs-spirit-m1-dust2.dem",
         "9z": "2394986-spirit-vs-9z-iem-cologne-major/spirit-vs-9z-m3-dust2.dem",
         "g2": "2394998-g2-vs-spirit-iem-cologne-major/g2-vs-spirit-m2-dust2.dem",
         "falcons": "2395001-spirit-vs-falcons-iem-cologne-major/spirit-vs-falcons-m3-dust2.dem"}
PROPS = ['X','Y','Z','pitch','yaw','health','is_alive','team_num','FORWARD','BACK','LEFT','RIGHT','FIRE','JUMP','DUCK','WALK','RELOAD','active_weapon_name','is_scoped','spotted','total_rounds_played','is_freeze_period','is_warmup_period','game_time','armor_value','has_helmet','balance']
for k, path in DEMOS.items():
    out = f"data/{k}_ticks.parquet"
    if os.path.exists(out): continue
    f = f"{k}.dem"
    if not os.path.exists(f): subprocess.run(["curl", "-sL", "-o", f, B + path], check=True)
    p = DemoParser(f)
    ticks = p.parse_ticks(PROPS)
    ticks = ticks[ticks.tick % 4 == 0]                      # 16 Hz
    ticks.to_parquet(out)
    for ev in ["player_death", "weapon_fire", "player_hurt", "round_freeze_end", "round_end", "bomb_planted", "smokegrenade_detonate", "flashbang_detonate", "grenade_thrown"]:
        try:
            e = p.parse_event(ev, player=["X", "Y", "Z", "team_num"])
            if len(e): e.to_parquet(f"data/{k}_{ev}.parquet")
        except Exception as ex: print(k, ev, "skip", str(ex)[:60])
    print(k, len(ticks), "rows", ticks.tick.max(), flush=True)
    os.remove(f)
