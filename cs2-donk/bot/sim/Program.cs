using System.Globalization;
using System.Numerics;
using DonkAI;
var ci = CultureInfo.InvariantCulture;
var model = GoalModel.Load("../DonkAI/donk_model.json");
// 1) parity with LightGBM
var lines = File.ReadAllLines("../sample.csv"); var head = lines[0].Split(',');
double maxErr = 0;
foreach (var l in lines.Skip(1)) {
    var v = l.Split(',').Select(s => s == "" ? double.NaN : double.Parse(s, ci)).ToArray();
    var pr = model.Probs(model.features.Select(n => v[Array.IndexOf(head, n)]).ToArray());
    for (int c = 0; c < pr.Length; c++) maxErr = Math.Max(maxErr, Math.Abs(pr[c] - v[Array.IndexOf(head, "p" + c)]));
}
Console.WriteLine($"parity: max abs prob diff vs LightGBM = {maxErr:G4} over {lines.Length - 1} rows");
// 2) closed-loop 2D rollout from spawn with the same brain + legs as the plugin
static float Wrap(float a) { a = (a + 180) % 360; if (a < 0) a += 360; return a - 180; }
var outp = new StreamWriter("../sim.csv"); outp.WriteLine("run,t,x,y,gx,gy,mode");
var starts = File.ReadAllLines("../spawns.txt").Select((l, i) => { var q = l.Split(',').Select(float.Parse).ToArray(); return ((q[0] == 2 ? "T" : "CT") + i, (int)q[0], q[1], q[2], q[0] == 2 ? 90f : -90f); }).ToArray();
foreach (var (name, team, sx, sy, syaw) in starts) {
    var s0 = Nav.Snap(Nav.Cell(sx, sy).Item1, Nav.Cell(sx, sy).Item2)!.Value; var c0 = Nav.Center(s0.Item1, s0.Item2);
    Vector2 pos = new((float)c0.Item1, (float)c0.Item2), vel = Vector2.Zero, steer = pos, goal = pos; float yaw = syaw, want = 0; string mode = "";
    var hist = new List<(float x, float y, float yaw)>(); int stuck = 0; var sref = pos; var probs = new double[model.classes]; int choice = -1;
    for (int tick = 0; tick < 64 * 40; tick++) {
        float t = tick / 64f;
        if (tick % 4 == 0) { hist.Add((pos.X, pos.Y, yaw)); if (hist.Count > 40) hist.RemoveAt(0); }
        if (tick % 8 == 0) {
            (float x, float y, float yaw) H(int k) => hist[Math.Max(0, hist.Count - 1 - k)];
            var f = new Dictionary<string, double> { ["X"] = pos.X, ["Y"] = pos.Y, ["Z"] = 0, ["vx"] = (pos.X - H(4).x) * 4, ["vy"] = (pos.Y - H(4).y) * 4, ["ysin"] = Math.Sin(yaw * Math.PI / 180), ["ycos"] = Math.Cos(yaw * Math.PI / 180), ["pitch"] = 2,
                ["hX0_5"] = pos.X - H(8).x, ["hY0_5"] = pos.Y - H(8).y, ["hX1"] = pos.X - H(16).x, ["hY1"] = pos.Y - H(16).y, ["hX2"] = pos.X - H(32).x, ["hY2"] = pos.Y - H(32).y, ["hyaw0_25"] = Wrap(yaw - H(4).yaw),
                ["tr"] = t, ["team_num"] = team, ["health"] = 100, ["armor_value"] = 100, ["wc"] = 2, ["mates"] = 4, ["enem"] = 5, ["planted"] = 0, ["ex"] = 0, ["ey"] = 0, ["ed"] = 4000, ["eang"] = 0, ["cx"] = 0, ["cy"] = 0, ["is_scoped"] = 0, ["isdonk"] = 1 };
            var pr = model.Probs(model.features.Select(n => f[n]).ToArray());
            for (int c = 0; c < pr.Length; c++) probs[c] = probs[c] * 0.6 + pr[c] * 0.4;
            int best = Array.IndexOf(probs, probs.Max()); if (choice < 0 || probs[best] > probs[choice] + 0.08) choice = best;
            if (choice == 0) { goal = pos; want = 0; mode = "hold"; } else { double a = model.SectorAngle(choice) * Math.PI / 180; goal = pos + new Vector2((float)(Math.Cos(a) * model.move_dist), (float)(Math.Sin(a) * model.move_dist)); want = 215; mode = "move"; }
            var s = Nav.Snap(Nav.Cell(pos.X, pos.Y).Item1, Nav.Cell(pos.X, pos.Y).Item2); var g = Nav.Snap(Nav.Cell(goal.X, goal.Y).Item1, Nav.Cell(goal.X, goal.Y).Item2);
            steer = goal; if (s != null && g != null) { var p = Nav.Path(s.Value, g.Value); if (p != null && p.Count > 1) { var st = Nav.Steer(p); var c = Nav.Center(st.Item1, st.Item2); steer = new((float)c.Item1, (float)c.Item2); } }
            outp.WriteLine(string.Join(",", name, t.ToString("F2", ci), pos.X.ToString("F0", ci), pos.Y.ToString("F0", ci), goal.X.ToString("F0", ci), goal.Y.ToString("F0", ci), mode));
            if (tick % 48 == 0) { if (mode == "move" && Vector2.Distance(pos, sref) < 25) stuck++; sref = pos; }
        }
        var to = steer - pos; var desired = to.Length() > 8 && want > 1 ? Vector2.Normalize(to) * MathF.Min(want, 245) : Vector2.Zero;
        vel = Vector2.Lerp(vel, desired, 0.22f);
        var np = pos + vel / 64f; var nc = Nav.Cell(np.X, np.Y);
        if (Grid.Get(0, nc.Item1, nc.Item2)) pos = np; else vel *= 0.3f;       // walls from the demo grid
        if (vel.Length() > 60) { float ty = MathF.Atan2(vel.Y, vel.X) * 180 / MathF.PI; yaw = Wrap(yaw + Math.Clamp(Wrap(ty - yaw) * 0.18f, -9f, 9f)); }
    }
    Console.WriteLine($"{name}: end ({pos.X:F0},{pos.Y:F0}), stuck checks {stuck}");
}
outp.Dispose();
