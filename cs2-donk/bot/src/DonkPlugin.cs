using System.Numerics;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Modules.Commands;

namespace DonkAI;

// Takes over one bot on a local server: the model trained on donk's demos picks where to go,
// A* over the demo-derived Dust2 grid gets there, and CS2's own bot AI handles gunfights.
public class DonkPlugin : BasePlugin {
    public override string ModuleName => "DonkAI";
    public override string ModuleVersion => "0.2.0";
    public override string ModuleDescription => "Bot driven by a model trained on donk's Dust2 demos";

    GoalModel? model;
    LookModel? look;
    double[] lookProbs = new double[36]; float lookYaw, lookPitch = 2, fightStart = -99; bool lookValid, preAim;
    CCSPlayerController? me;
    readonly List<(float x, float y, float yaw)> hist = new();           // 16 Hz samples of the controlled bot
    float freezeEnd, lastCombat = -99, lastEnemySeen = -99, enemyYaw, stuckUntil = -99;
    bool planted, debug = true;
    int tick;
    Brain? brain; int stuckCount;
    Vector2 goal, steer, vel; float wantSpeed, yaw, pitch; string mode = "idle";
    (float x, float y, float t) stuckRef;
    StreamWriter? log;

    public override void Load(bool hotReload) {
        model = GoalModel.Load(Path.Combine(ModuleDirectory, "donk_model.json")); brain = new Brain(model);
        look = LookModel.Load(Path.Combine(ModuleDirectory, "donk_look.json")); lookProbs = new double[look.classes];
        Directory.CreateDirectory(Path.Combine(ModuleDirectory, "logs"));
        RegisterListener<Listeners.OnTick>(OnTick);
        RegisterEventHandler<EventRoundFreezeEnd>((e, i) => { freezeEnd = Server.CurrentTime; planted = false; hist.Clear(); lastCombat = -99; brain?.Reset(); Array.Clear(lookProbs); lookValid = false; return HookResult.Continue; });
        RegisterEventHandler<EventBombPlanted>((e, i) => { planted = true; return HookResult.Continue; });
        AddCommand("css_donk", "Hand a bot to the donk model: css_donk [bot name]", CmdDonk);
        AddCommand("css_donk_off", "Give the bot back to the game AI", (p, i) => { me = null; i.ReplyToCommand("[DonkAI] off"); });
        AddCommand("css_donk_debug", "Toggle chat debug", (p, i) => { debug = !debug; i.ReplyToCommand($"[DonkAI] debug {debug}"); });
        Console.WriteLine($"[DonkAI] loaded model: {model.trees.Length} trees, {model.features.Length} features");
    }

    void CmdDonk(CCSPlayerController? caller, CommandInfo info) {
        string want = info.ArgCount > 1 ? info.ArgString.Trim().ToLowerInvariant() : "";
        var bots = Utilities.GetPlayers().Where(p => p.IsValid && p.IsBot).ToList();
        me = want.Length > 0 ? bots.FirstOrDefault(b => b.PlayerName.ToLowerInvariant().Contains(want)) : bots.FirstOrDefault(b => b.TeamNum == 2) ?? bots.FirstOrDefault();
        if (me == null) { info.ReplyToCommand("[DonkAI] no bot found. Add one with bot_add_t"); return; }
        hist.Clear(); freezeEnd = Server.CurrentTime;
        log?.Dispose(); log = new StreamWriter(Path.Combine(ModuleDirectory, "logs", $"run_{DateTime.Now:yyyyMMdd_HHmmss}.csv")) { AutoFlush = true };
        log.WriteLine("time,tr,x,y,z,yaw,look_yaw,pitch,look_pitch,goal_x,goal_y,steer_x,steer_y,want_speed,speed,mode,place");
        info.ReplyToCommand($"[DonkAI] now driving {me.PlayerName} ({(me.TeamNum == 2 ? "T" : "CT")})");
        Server.PrintToChatAll($" [DonkAI] бот {me.PlayerName} теперь под управлением модели donk");
    }

    static int WeaponClass(string? d) {
        d = (d ?? "").Replace("weapon_", "");
        if (d is "awp" or "ssg08") return 1;
        if (d is "ak47" or "m4a1" or "m4a1_silencer" or "galilar" or "famas" or "aug" or "sg556") return 2;
        if (d is "mac10" or "mp9" or "mp7" or "ump45" or "p90" or "bizon" or "mp5sd") return 3;
        if (d is "deagle" or "glock" or "usp_silencer" or "hkp2000" or "p250" or "fiveseven" or "tec9" or "cz75a" or "elite" or "revolver") return 4;
        if (d is "hegrenade" or "flashbang" or "smokegrenade" or "molotov" or "incgrenade" or "decoy") return 5;
        if (d is "c4") return 6;
        return 0;
    }
    static float Wrap(float a) { a = (a + 180) % 360; if (a < 0) a += 360; return a - 180; }

    void OnTick() {
        tick++;
        if (me == null || !me.IsValid || model == null) return;
        var pawn = me.PlayerPawn.Value;
        if (pawn == null || !pawn.IsValid || !me.PawnIsAlive || pawn.AbsOrigin == null) { mode = "dead"; return; }
        float now = Server.CurrentTime, x = pawn.AbsOrigin.X, y = pawn.AbsOrigin.Y, z = pawn.AbsOrigin.Z;
        var eye = pawn.EyeAngles; float curYaw = eye.Y, curPitch = eye.X;

        // who can see whom: an enemy spotted by *this* bot means a gunfight -> leave it to the game AI
        int team = me.TeamNum; var players = Utilities.GetPlayers().Where(p => p.IsValid && p.PawnIsAlive && p.PlayerPawn.Value != null && p.PlayerPawn.Value.AbsOrigin != null).ToList();
        bool fight = false; float ex = 0, ey = 0, ed = 4000;
        foreach (var p in players.Where(p => p.TeamNum != team && p.TeamNum >= 2)) {
            var pp = p.PlayerPawn.Value!; var o = pp.AbsOrigin!; float dx = o.X - x, dy = o.Y - y, dist = MathF.Sqrt(dx * dx + dy * dy);
            var mask = pp.EntitySpottedState.SpottedByMask; int s = me.Slot;
            bool seenByMe = s >= 0 && s / 32 < mask.Length && (mask[s / 32] & (1u << (s % 32))) != 0;
            if (seenByMe && dist < 3500) { fight = true; enemyYaw = MathF.Atan2(dy, dx) * 180 / MathF.PI; }
            if (pp.EntitySpottedState.Spotted && dist < ed) { ed = dist; ex = dx; ey = dy; lastEnemySeen = now; }
        }
        if (fight) { if (now - lastCombat > 1.2f) fightStart = now; lastCombat = now; }
        preAim = !fight && ed < 1600;

        if (tick % 4 == 0) {                                   // 16 Hz: history + model features
            hist.Add((x, y, curYaw)); if (hist.Count > 40) hist.RemoveAt(0);
            if (tick % 8 == 0) Decide(pawn, players, team, x, y, z, curYaw, curPitch, ex, ey, ed, now);
            log?.WriteLine(string.Join(",", now.ToString("F2"), (now - freezeEnd).ToString("F2"), x.ToString("F0"), y.ToString("F0"), z.ToString("F0"), curYaw.ToString("F0"), lookYaw.ToString("F0"), curPitch.ToString("F1"), lookPitch.ToString("F1"), goal.X.ToString("F0"), goal.Y.ToString("F0"),
                steer.X.ToString("F0"), steer.Y.ToString("F0"), wantSpeed.ToString("F0"), new Vector2(pawn.AbsVelocity.X, pawn.AbsVelocity.Y).Length().ToString("F0"), mode, pawn.LastPlaceName));
        }

        if (fight) {                                                                                  // counter-strafe: stand still while the game AI aims and shoots
            mode = "fight"; vel = Vector2.Zero; yaw = curYaw; pitch = curPitch;
            pawn.Teleport((Vector3?)null, (Vector3?)null, new Vector3(0, 0, pawn.AbsVelocity.Z)); return;
        }
        if (now - lastCombat < 1.2f) { mode = "after-fight"; vel = new Vector2(pawn.AbsVelocity.X, pawn.AbsVelocity.Y); yaw = curYaw; pitch = curPitch; return; }

        // legs: accelerate toward the steering point, never faster than a rifle run
        var to = steer - new Vector2(x, y); float dist2 = to.Length();
        var desired = dist2 > 8 && wantSpeed > 1 ? Vector2.Normalize(to) * MathF.Min(wantSpeed, 245) : Vector2.Zero;
        vel = Vector2.Lerp(vel, desired, 0.22f);
        float vz = pawn.AbsVelocity.Z;
        if (now < stuckUntil && MathF.Abs(vz) < 1) { vz = 300; stuckUntil = -99; }           // hop over a lip we are stuck on
        // eyes: look where we walk, or toward the last enemy when holding; turn like a human, not a snap
        // crosshair: pre-aim an enemy a teammate sees nearby, otherwise hold donk's usual angle for this spot
        float targetYaw = preAim ? MathF.Atan2(ey, ex) * 180 / MathF.PI : lookValid ? lookYaw : (vel.Length() > 60 ? MathF.Atan2(vel.Y, vel.X) * 180 / MathF.PI : yaw);
        float dyaw = Wrap(targetYaw - yaw); yaw = Wrap(yaw + Math.Clamp(dyaw * 0.18f, -9f, 9f));
        pitch += ((lookValid ? lookPitch : 2f) - pitch) * 0.1f;
        pawn.Teleport(null, new Vector3(pitch, yaw, 0), new Vector3(vel.X, vel.Y, vz));
    }

    void Decide(CCSPlayerPawn pawn, List<CCSPlayerController> players, int team, float x, float y, float z, float curYaw, float curPitch, float ex, float ey, float ed, float now) {
        (float x, float y, float yaw) H(int k) => hist[Math.Max(0, hist.Count - 1 - k)];
        var mates = players.Where(p => p.TeamNum == team).ToList();
        float cx = mates.Average(p => p.PlayerPawn.Value!.AbsOrigin!.X) - x, cy = mates.Average(p => p.PlayerPawn.Value!.AbsOrigin!.Y) - y;
        int enemies = players.Count(p => p.TeamNum != team && p.TeamNum >= 2);
        float yr = curYaw * MathF.PI / 180;
        var f = new Dictionary<string, double> {
            ["X"] = x, ["Y"] = y, ["Z"] = z, ["vx"] = (x - H(4).x) * 4, ["vy"] = (y - H(4).y) * 4, ["ysin"] = Math.Sin(yr), ["ycos"] = Math.Cos(yr), ["pitch"] = curPitch,
            ["hX0_5"] = x - H(8).x, ["hY0_5"] = y - H(8).y, ["hX1"] = x - H(16).x, ["hY1"] = y - H(16).y, ["hX2"] = x - H(32).x, ["hY2"] = y - H(32).y,
            ["hyaw0_25"] = Wrap(curYaw - H(4).yaw), ["tr"] = now - freezeEnd, ["team_num"] = team, ["health"] = pawn.Health, ["armor_value"] = pawn.ArmorValue,
            ["wc"] = WeaponClass(pawn.WeaponServices?.ActiveWeapon.Value?.DesignerName), ["mates"] = mates.Count - 1, ["enem"] = enemies, ["planted"] = planted ? 1 : 0,
            ["ex"] = ex, ["ey"] = ey, ["ed"] = ed, ["eang"] = ed < 4000 ? Wrap(MathF.Atan2(ey, ex) * 180 / MathF.PI - curYaw) : 0, ["cx"] = cx, ["cy"] = cy,
            ["is_scoped"] = pawn.IsScoped ? 1 : 0, ["isdonk"] = 1 };
        if (look != null) {
            var lp = look.Probs(look.features.Select(n => f[n]).ToArray());
            for (int c = 0; c < lp.Length; c++) lookProbs[c] = lookProbs[c] * 0.7 + lp[c] * 0.3;
            lookYaw = (float)look.Yaw(lookProbs); lookPitch = (float)look.Pitch(look.features.Select(n => f[n]).ToArray()); lookValid = true;
        }
        brain!.Decide(model!.features.Select(n => f[n]).ToArray(), new Vector2(x, y), now);
        goal = brain.Goal; steer = brain.Steer; wantSpeed = brain.WantSpeed; mode = brain.Mode;
        float len = (goal - new Vector2(x, y)).Length();

        // stuck: wanted to run but barely moved for ~0.75 s -> hop
        if (now - stuckRef.t > 0.75f) {
            float moved = MathF.Sqrt((x - stuckRef.x) * (x - stuckRef.x) + (y - stuckRef.y) * (y - stuckRef.y));
            if (mode == "move" && moved < 25 && now - lastCombat > 1.2f) { stuckUntil = now + 0.3f; if (++stuckCount >= 2) { brain!.Stuck(now); stuckCount = 0; } } else stuckCount = 0;
            stuckRef = (x, y, now);
        }
        if (debug && tick % 128 == 0) Server.PrintToChatAll($" [DonkAI] {mode} → {pawn.LastPlaceName} ({len:F0}u за 2с)");
    }

    public override void Unload(bool hotReload) { log?.Dispose(); }
}
