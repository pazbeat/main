using System.Globalization;
using System.Numerics;
using System.Text.Json;
using DonkAI;
// Scenario bench: the same Brain the plugin uses, driven through scripted situations in a 2D Dust2
// (walls and heights learned from demos). Output: one trace row per decision for analysis.
var ci = CultureInfo.InvariantCulture;
var model = GoalModel.Load(args.Length > 0 ? args[0] : "../DonkAI/donk_model.json");
var look = LookModel.Load("../DonkAI/donk_look.json");
var strat = args.Length > 3 ? StrategyModel.Load(args[3]) : null;
var scen = JsonSerializer.Deserialize<List<Scenario>>(File.ReadAllText(args.Length > 1 ? args[1] : "../scenarios.json"), new JsonSerializerOptions { PropertyNameCaseInsensitive = true })!;
var zoneNames = System.Text.Json.JsonDocument.Parse(File.ReadAllText("../DonkAI/donk_strat.json")).RootElement.GetProperty("zones").EnumerateArray().Select(e => e.GetString()!).ToArray();
var zg = new Dictionary<(int, int), float>();
foreach (var l in File.ReadAllLines("../zgrid.csv")) { var q = l.Split(','); zg[(int.Parse(q[0]), int.Parse(q[1]))] = float.Parse(q[2], ci); }
var mo = new Dictionary<(int, string, int), Vector2>();   // where teammates usually are, relative to a player in this zone (from real matches)
foreach (var l in File.ReadAllLines("../mate_offsets.csv")) { var q = l.Split(','); mo[(int.Parse(q[0]), q[1], int.Parse(q[2]))] = new Vector2(float.Parse(q[3], ci), float.Parse(q[4], ci)); }
float Zat(Vector2 p, float last) => zg.TryGetValue(Nav.Cell(p.X, p.Y), out var z) ? z : last;
static float Wrap(float a) { a = (a + 180) % 360; if (a < 0) a += 360; return a - 180; }
var outp = new StreamWriter(args.Length > 2 ? args[2] : "../scen_trace.csv");
outp.WriteLine("scenario,seed,t,x,y,mode,goal_x,goal_y,look_yaw,planted,enemies_seen,stuck,zone,target_zone");
var sw = System.Diagnostics.Stopwatch.StartNew(); long decisions = 0;
foreach (var sc in scen) for (int seed = 1; seed <= sc.Seeds; seed++) {
    var rnd = new Random(seed * 7919 + sc.Name.Length);
    var start = sc.Starts[(seed - 1) % sc.Starts.Length];
    var sc0 = Nav.Snap(Nav.Cell(start[0], start[1]).Item1, Nav.Cell(start[0], start[1]).Item2); if (sc0 == null) continue;
    var c0 = Nav.Center(sc0.Value.Item1, sc0.Value.Item2);
    Vector2 pos = new((float)c0.Item1, (float)c0.Item2), vel = Vector2.Zero; float yaw = sc.Team == 2 ? 90 : -90, z = 0;
    var brain = new Brain(model, seed); var brain3 = strat == null ? null : new Brain3(strat, model, seed); var hist = new List<(float x, float y, float yaw)>(); int stuckRow = 0; var sref = pos; var lookProbs = new double[look.classes];
    for (int tick = 0; tick < (int)(sc.Duration * 64); tick++) {
        float t = sc.T0 + tick / 64f;
        if (tick % 4 == 0) { hist.Add((pos.X, pos.Y, yaw)); if (hist.Count > 40) hist.RemoveAt(0); }
        if (tick % 8 == 0) {
            (float x, float y, float yaw) H(int k) => hist[Math.Max(0, hist.Count - 1 - k)];
            bool planted = sc.Bomb != null && t >= sc.Bomb.T; var bomb = sc.Bomb == null ? Vector2.Zero : new Vector2(sc.Bomb.X, sc.Bomb.Y);
            var seen = (sc.Enemies ?? []).Where(e => t >= e.From && t <= e.To).Select(e => new Vector2(e.X, e.Y) - pos).OrderBy(v => v.Length()).ToList();
            var en = seen.Count > 0 ? seen[0] : Vector2.Zero; float ed = seen.Count > 0 ? en.Length() : 4000;
            int mates = sc.MatesAfter != null && t >= sc.MatesAfter.T ? sc.MatesAfter.N : sc.Mates;
            var zi = Zones.At(pos.X, pos.Y); string zn = zi >= 0 ? zoneNames[zi] : "";
            var mc = mates == 0 ? pos : sc.MateCenter != null ? new Vector2(sc.MateCenter[0], sc.MateCenter[1]) : pos + (mo.TryGetValue((sc.Team, zn, planted ? 1 : 0), out var off) ? off : Vector2.Zero);
            z = Zat(pos, z); float yr = yaw * MathF.PI / 180;
            var f = new Dictionary<string, double> { ["X"] = pos.X, ["Y"] = pos.Y, ["Z"] = z, ["vx"] = (pos.X - H(4).x) * 4, ["vy"] = (pos.Y - H(4).y) * 4, ["tr"] = t, ["team_num"] = sc.Team,
                ["health"] = sc.Health, ["armor_value"] = 100, ["wc"] = 2, ["mates"] = mates, ["enem"] = sc.EnemiesAlive, ["planted"] = planted ? 1 : 0,
                ["ex"] = en.X, ["ey"] = en.Y, ["ed"] = ed, ["eang"] = ed < 4000 ? Wrap(MathF.Atan2(en.Y, en.X) * 180 / MathF.PI - yaw) : 0,
                ["cx"] = mc.X - pos.X, ["cy"] = mc.Y - pos.Y, ["is_scoped"] = 0, ["isdonk"] = 1, ["ysin"] = Math.Sin(yr), ["ycos"] = Math.Cos(yr), ["pitch"] = 2 };
            float bdx = planted ? bomb.X - pos.X : 0, bdy = planted ? bomb.Y - pos.Y : 0;
            f["bdx"] = bdx; f["bdy"] = bdy; f["bd"] = planted ? MathF.Sqrt(bdx * bdx + bdy * bdy) : 4000; f["bang"] = planted ? MathF.Atan2(bdy, bdx) * 180 / MathF.PI : -999; f["tp"] = planted ? t - sc.Bomb!.T : -1;
            var li = model.features.Select(n => f.TryGetValue(n, out var v) ? v : 0).ToArray();
            if (brain3 != null) brain3.Decide(strat!.features.Select(n => f.TryGetValue(n, out var v) ? v : 0).ToArray(), li, pos, t, planted, ed); else brain.Decide(li, pos, t);
            decisions++;
            string mode = brain3?.Mode ?? brain.Mode; var goalP = brain3?.Goal ?? brain.Goal; var steerP = brain3?.Steer ?? brain.Steer; float want = brain3?.WantSpeed ?? brain.WantSpeed;
            var lp = look.Probs(look.features.Select(n => f.TryGetValue(n, out var v) ? v : 0).ToArray());
            for (int c = 0; c < lp.Length; c++) lookProbs[c] = lookProbs[c] * 0.7 + lp[c] * 0.3;
            bool stuckNow = false;
            if (tick % 48 == 0 && tick > 0) { if (mode != "hold" && Vector2.Distance(pos, sref) < 25) { stuckNow = true; if (++stuckRow >= 2) { if (brain3 != null) brain3.Stuck(t); else brain.Stuck(t); stuckRow = 0; } } else stuckRow = 0; sref = pos; }
            outp.WriteLine(string.Join(",", "\"" + sc.Name + "\"", seed, t.ToString("F2", ci), pos.X.ToString("F0", ci), pos.Y.ToString("F0", ci), mode, goalP.X.ToString("F0", ci), goalP.Y.ToString("F0", ci),
                look.Yaw(lookProbs).ToString("F0", ci), planted ? 1 : 0, seen.Count, stuckNow ? 1 : 0, brain3?.CurrentZone ?? "", brain3?.TargetZone ?? ""));
        }
        var steerNow = brain3?.Steer ?? brain.Steer; float wantNow = brain3?.WantSpeed ?? brain.WantSpeed;
        if (Environment.GetEnvironmentVariable("DBG") == "1" && tick % 16 == 0) Console.WriteLine($"t={t:F2} pos=({pos.X:F0},{pos.Y:F0}) steer=({steerNow.X:F0},{steerNow.Y:F0}) want={wantNow} vel=({vel.X:F0},{vel.Y:F0}) mode={brain3?.Mode}");
        var to = steerNow - pos; var desired = to.Length() > 8 && wantNow > 1 ? Vector2.Normalize(to) * MathF.Min(wantNow, 245) : Vector2.Zero;
        vel = Vector2.Lerp(vel, desired, 0.22f);
        var np = pos + vel / 64f; var nc = Nav.Cell(np.X, np.Y);
        if (Grid.Get(0, nc.Item1, nc.Item2)) pos = np;
        else { var nx = new Vector2(np.X, pos.Y); var ny = new Vector2(pos.X, np.Y); var cxp = Nav.Cell(nx.X, nx.Y); var cyp = Nav.Cell(ny.X, ny.Y);
            if (Grid.Get(0, cxp.Item1, cxp.Item2)) { pos = nx; vel.Y = 0; } else if (Grid.Get(0, cyp.Item1, cyp.Item2)) { pos = ny; vel.X = 0; } else vel *= 0.3f; }   // slide along the wall
        if (vel.Length() > 60) { float ty = MathF.Atan2(vel.Y, vel.X) * 180 / MathF.PI; yaw = Wrap(yaw + Math.Clamp(Wrap(ty - yaw) * 0.18f, -9f, 9f)); }
    }
}
outp.Dispose();
Console.WriteLine($"scenarios {scen.Count}, decisions {decisions}, {sw.Elapsed.TotalMilliseconds / Math.Max(1, decisions):F2} ms per decision");

public sealed class Scenario {
    public string Name { get; set; } = ""; public int Team { get; set; } = 2; public float[][] Starts { get; set; } = []; public float T0 { get; set; }
    public float Duration { get; set; } = 30; public int Seeds { get; set; } = 8; public int Health { get; set; } = 100; public int Mates { get; set; } = 4;
    public int EnemiesAlive { get; set; } = 5; public float[]? MateCenter { get; set; }
    public BombInfo? Bomb { get; set; } public List<EnemyInfo>? Enemies { get; set; } public MatesChange? MatesAfter { get; set; }
}
public sealed class BombInfo { public float T { get; set; } public float X { get; set; } public float Y { get; set; } }
public sealed class EnemyInfo { public float X { get; set; } public float Y { get; set; } public float From { get; set; } public float To { get; set; } = 999; }
public sealed class MatesChange { public float T { get; set; } public int N { get; set; } }
