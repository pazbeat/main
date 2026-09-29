using System.Globalization;
using System.Numerics;
using DonkAI;
var ci = CultureInfo.InvariantCulture;
var model = GoalModel.Load("../DonkAI/donk_model.json");
// 1) parity with LightGBM
var lines = File.ReadAllLines("../sample_intent.csv"); var head = lines[0].Split(',');
double maxErr = 0;
foreach (var l in lines.Skip(1)) {
    var v = l.Split(',').Select(s => s == "" ? double.NaN : double.Parse(s, ci)).ToArray();
    var pr = model.Probs(model.features.Select(n => v[Array.IndexOf(head, n)]).ToArray());
    for (int c = 0; c < pr.Length; c++) maxErr = Math.Max(maxErr, Math.Abs(pr[c] - v[Array.IndexOf(head, "p" + c)]));
}
Console.WriteLine($"parity intent: max abs prob diff vs LightGBM = {maxErr:G4} over {lines.Length - 1} rows");
var look = LookModel.Load("../DonkAI/donk_look.json"); double le = 0, pe = 0; lines = File.ReadAllLines("../sample.csv"); head = lines[0].Split(',');
foreach (var l in lines.Skip(1)) {
    var v = l.Split(',').Select(s => s == "" ? double.NaN : double.Parse(s, ci)).ToArray();
    var x = look.features.Select(n => v[Array.IndexOf(head, n)]).ToArray(); var pr = look.Probs(x);
    for (int c = 0; c < pr.Length; c++) le = Math.Max(le, Math.Abs(pr[c] - v[Array.IndexOf(head, "l" + c)]));
    pe = Math.Max(pe, Math.Abs(look.Pitch(x) - v[Array.IndexOf(head, "pp")]));
}
Console.WriteLine($"parity look: max abs prob diff {le:G4}, pitch diff {pe:G4}");
// 2) closed-loop 2D rollout from spawn with the same brain + legs as the plugin
static float Wrap(float a) { a = (a + 180) % 360; if (a < 0) a += 360; return a - 180; }
var outp = new StreamWriter("../sim.csv"); outp.WriteLine("run,t,x,y,gx,gy,mode");
var starts = File.ReadAllLines("../spawns.txt").Select((l, i) => { var q = l.Split(',').Select(float.Parse).ToArray(); return ((q[0] == 2 ? "T" : "CT") + i, (int)q[0], q[1], q[2], q[0] == 2 ? 90f : -90f); }).ToArray();
var zg = new Dictionary<(int, int), float>();
foreach (var l in File.ReadAllLines("../zgrid.csv")) { var q = l.Split(','); zg[(int.Parse(q[0]), int.Parse(q[1]))] = float.Parse(q[2], ci); }
float Zat(Vector2 p, float last) { var c = Nav.Cell(p.X, p.Y); return zg.TryGetValue(c, out var z) ? z : last; }
int totalStuck = 0; var sw = System.Diagnostics.Stopwatch.StartNew(); long decisions = 0;
foreach (var seed in new[] { 1, 2, 3 })
foreach (var (name0, team, sx, sy, syaw) in starts) {
    string name = name0 + "_s" + seed;
    var brain = new Brain(model, seed);
    var s0 = Nav.Snap(Nav.Cell(sx, sy).Item1, Nav.Cell(sx, sy).Item2)!.Value; var c0 = Nav.Center(s0.Item1, s0.Item2);
    Vector2 pos = new((float)c0.Item1, (float)c0.Item2), vel = Vector2.Zero; float yaw = syaw, zz = 0;
    var hist = new List<(float x, float y, float yaw)>(); int stuck = 0, stuckRow = 0; var sref = pos;
    for (int tick = 0; tick < 64 * 40; tick++) {
        float t = tick / 64f;
        if (tick % 4 == 0) { hist.Add((pos.X, pos.Y, yaw)); if (hist.Count > 40) hist.RemoveAt(0); }
        if (tick % 8 == 0) {
            (float x, float y, float yaw) H(int k) => hist[Math.Max(0, hist.Count - 1 - k)];
            zz = Zat(pos, zz); var f = new Dictionary<string, double> { ["X"] = pos.X, ["Y"] = pos.Y, ["Z"] = zz, ["vx"] = (pos.X - H(4).x) * 4, ["vy"] = (pos.Y - H(4).y) * 4, ["tr"] = t, ["team_num"] = team, ["health"] = 100, ["armor_value"] = 100, ["wc"] = 2,
                ["mates"] = 4, ["enem"] = 5, ["planted"] = 0, ["ex"] = 0, ["ey"] = 0, ["ed"] = 4000, ["eang"] = 0, ["cx"] = 0, ["cy"] = 0, ["is_scoped"] = 0, ["isdonk"] = 1 };
            brain.Decide(model.features.Select(n => f[n]).ToArray(), pos, t); decisions++;
            outp.WriteLine(string.Join(",", name, t.ToString("F2", ci), pos.X.ToString("F0", ci), pos.Y.ToString("F0", ci), brain.Goal.X.ToString("F0", ci), brain.Goal.Y.ToString("F0", ci), brain.Mode));
            if (tick % 48 == 0) { if (brain.Mode == "move" && Vector2.Distance(pos, sref) < 25) { stuck++; if (++stuckRow >= 2) { brain.Stuck(t); stuckRow = 0; } } else stuckRow = 0; sref = pos; }
        }
        var to = brain.Steer - pos; var desired = to.Length() > 8 && brain.WantSpeed > 1 ? Vector2.Normalize(to) * MathF.Min(brain.WantSpeed, 245) : Vector2.Zero;
        vel = Vector2.Lerp(vel, desired, 0.22f);
        var np = pos + vel / 64f; var nc = Nav.Cell(np.X, np.Y);
        if (Grid.Get(0, nc.Item1, nc.Item2)) pos = np; else vel *= 0.3f;
        if (vel.Length() > 60) { float ty = MathF.Atan2(vel.Y, vel.X) * 180 / MathF.PI; yaw = Wrap(yaw + Math.Clamp(Wrap(ty - yaw) * 0.18f, -9f, 9f)); }
    }
    totalStuck += stuck; Console.WriteLine($"{name}: end ({pos.X:F0},{pos.Y:F0}), stuck checks {stuck}");
}
Console.WriteLine($"total stuck checks {totalStuck}; decision time {sw.Elapsed.TotalMilliseconds / decisions:F2} ms avg (incl. sim)");
outp.Dispose();
