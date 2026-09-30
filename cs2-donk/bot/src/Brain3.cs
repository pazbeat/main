using System.Numerics;
namespace DonkAI;

// Two layers, like a player thinks: once a second "which zone should I be in 10 s from now" (strategy model),
// then either travel there along a path, or, when already there, the short-term brain decides hold / small moves.
public sealed class Brain3 {
    readonly StrategyModel strat; readonly Brain local; readonly Random rng;
    double[] zp; int target = -1; bool paused; Vector2 heading, lastPos; float lastPosT = -99; float nextStrat = -1; List<(int, int)>? path; int pathTarget = -1;
    public Vector2 Goal, Steer; public float WantSpeed; public string Mode = "idle"; public string TargetZone = ""; public string CurrentZone = "";
    public Brain3(StrategyModel s, GoalModel g, int seed = 0) { strat = s; local = new Brain(g, seed); rng = seed == 0 ? new Random() : new Random(seed + 101); zp = new double[s.zones.Length]; }
    public void Reset() { target = -1; nextStrat = -1; path = null; Array.Clear(zp); local.Reset(); heading = Vector2.Zero; lastPosT = -99; }
    public void Stuck(float now) { path = null; local.Stuck(now); }

    public void Decide(double[] stratInput, double[] localInput, Vector2 pos, float now, bool planted = false, float enemyDist = 4000) {
        int here = Zones.At(pos.X, pos.Y); CurrentZone = here >= 0 ? strat.zones[here] : "";
        if (now - lastPosT >= 1f) { var mv = pos - lastPos; if (mv.Length() > 60) heading = Vector2.Normalize(mv); lastPos = pos; lastPosT = now; }
        if (now >= nextStrat) {
            nextStrat = now + 1f;
            var p = strat.Probs(stratInput);
            for (int c = 0; c < p.Length; c++) zp[c] = target < 0 ? p[c] : zp[c] * 0.5 + p[c] * 0.5;
            bool reached = target < 0 || target == here;
            bool implausible = target >= 0 && target != here && zp[target] < 0.04;                  // the situation changed (bomb elsewhere, enemies...)
            if (reached || implausible) {
                // next zone by probability (staying here is one of the options). Early in the round the plan is varied
                // so rounds differ; later the bot sticks to the most likely plan. Turning back needs a good reason.
                double pw = (!planted && now < 25) ? 1 : 4; var w = new double[zp.Length]; double tot = 0;
                for (int c = 0; c < zp.Length; c++) {
                    w[c] = Math.Pow(zp[c], pw);
                    if (c != here && heading.LengthSquared() > 0) { var d = new Vector2(strat.targets[c][0], strat.targets[c][1]) - pos; if (d.LengthSquared() > 1 && Vector2.Dot(Vector2.Normalize(d), heading) < -0.5f) w[c] *= 0.3; }
                    tot += w[c];
                }
                double r = rng.NextDouble() * tot, acc = 0; target = here;
                for (int c = 0; c < zp.Length; c++) { acc += w[c]; if (r <= acc) { target = c; break; } }
            }
            TargetZone = target >= 0 ? strat.zones[target] : "";
        }
        if (enemyDist < 1000) {                                                                   // contact: tactics beat the plan, the short-term brain reacts to the enemy
            path = null; local.Decide(localInput, pos, now);
            Goal = local.Goal; Steer = local.Steer; WantSpeed = local.WantSpeed; Mode = local.Mode == "hold" ? "hold" : "contact"; return;
        }
        if (target < 0 || target == here) {                                                      // already where we want to be: hold angles / small moves
            path = null; local.Decide(localInput, pos, now);
            bool leaves = local.Mode != "hold" && Zones.At(local.Steer.X, local.Steer.Y) != here;   // small moves stay inside the chosen zone
            if (local.Mode == "hold" || leaves) { Goal = Steer = pos; WantSpeed = 0; Mode = "hold"; return; }
            Goal = local.Goal; Steer = local.Steer; WantSpeed = local.WantSpeed; Mode = "adjust"; return;
        }
        // on the way: pause to check an angle when the short-term model is sure a player would stand here
        local.Decide(localInput, pos, now);
        if (paused ? local.PHold > 0.45 : local.PHold > 0.62) { paused = true; Goal = Steer = pos; WantSpeed = 0; Mode = "hold"; return; }
        paused = false;
        // travel to the zone's most-used spot along a path through the whole map
        var tp = strat.targets[target]; var goal = new Vector2(tp[0], tp[1]);
        var s = Nav.Snap(Nav.Cell(pos.X, pos.Y).Item1, Nav.Cell(pos.X, pos.Y).Item2); var g = Nav.Snap(Nav.Cell(goal.X, goal.Y).Item1, Nav.Cell(goal.X, goal.Y).Item2);
        if (s == null || g == null) { local.Decide(localInput, pos, now); Goal = local.Goal; Steer = local.Steer; WantSpeed = local.WantSpeed; Mode = local.Mode; return; }
        if (path == null || pathTarget != target || path.Count < 2) { path = Nav.Path(s.Value, g.Value, 60000); pathTarget = target; }
        if (path == null) { target = here; local.Decide(localInput, pos, now); Goal = local.Goal; Steer = local.Steer; WantSpeed = local.WantSpeed; Mode = local.Mode; return; }
        int k = 0; double bd = double.MaxValue;                                                    // drop the part of the path already walked
        for (int i = 0; i < Math.Min(path.Count, 80); i++) { double d = Math.Abs(path[i].Item1 - s.Value.Item1) + Math.Abs(path[i].Item2 - s.Value.Item2); if (d < bd) { bd = d; k = i; } }
        if (bd > 6) { path = Nav.Path(s.Value, g.Value, 60000); k = 0; if (path == null) return; }
        else path = path.GetRange(k, path.Count - k);
        var st = path.Count > 1 ? Nav.Steer(path) : g.Value;
        var hc = Nav.Cell(pos.X, pos.Y); if (!Grid.Get(1, hc.Item1, hc.Item2) || !Nav.Clear(hc, st)) st = path[Math.Min(1, path.Count - 1)];   // hugging a wall: next cell first
        var sc = Nav.Center(st.Item1, st.Item2);
        Goal = goal; Steer = new Vector2((float)sc.Item1, (float)sc.Item2); WantSpeed = 225; Mode = "travel";
    }
}
