using System.Numerics;
namespace DonkAI;

// Decision + route logic shared by the plugin and the offline simulator.
public sealed class Brain {
    readonly GoalModel model; readonly Random rng;
    readonly double[] probs; readonly float[] blockedUntil;
    public int Choice { get; private set; } = -1;
    public Vector2 Goal, Steer; public float WantSpeed; public string Mode = "idle";
    public double PHold => probs[0];                                                     // smoothed "stand still" probability
    public Brain(GoalModel m, int seed = 0) { model = m; probs = new double[m.classes]; blockedUntil = new float[m.classes]; rng = seed == 0 ? new Random() : new Random(seed); }
    public void Reset() { Choice = -1; Array.Clear(probs); Array.Clear(blockedUntil); }
    // the current direction led nowhere: forbid it for a moment
    public void Stuck(float now) { if (Choice > 0) { blockedUntil[Choice] = now + 2f; Choice = -1; } }

    public void Decide(double[] input, Vector2 pos, float now) {
        var pr = model.Probs(input);
        for (int c = 0; c < pr.Length; c++) probs[c] = probs[c] * 0.6 + pr[c] * 0.4;       // smooth over ~0.5 s so the bot commits
        bool Allowed(int c) => blockedUntil[c] <= now;
        // step 1: move or hold? "move" is all 8 directions together, not each one against "hold"
        double pMove = 1 - probs[0];
        bool moving = Choice > 0 ? pMove > 0.42 : pMove > 0.58;                              // hysteresis so the bot does not twitch
        if (Choice < 0) moving = rng.NextDouble() < 1 - pr[0];                                   // new round / blocked: decide by probability
        // step 2: which way
        if (!moving) Choice = 0;
        else if (Choice <= 0 || !Allowed(Choice)) {                                               // pick a route by its probability so rounds differ
            double tot = 0; for (int c = 1; c < pr.Length; c++) if (Allowed(c)) tot += probs[c];
            double r = rng.NextDouble() * tot, acc = 0; Choice = -1;
            for (int c = 1; c < pr.Length; c++) { if (!Allowed(c)) continue; acc += probs[c]; if (r <= acc) { Choice = c; break; } }
            if (Choice < 0) Choice = 0;
        } else {
            int best = -1; for (int c = 1; c < probs.Length; c++) if (Allowed(c) && (best < 0 || probs[c] > probs[best])) best = c;
            if (best > 0 && probs[best] > probs[Choice] + 0.05) Choice = best;                    // switch direction only for a clearly better one
        }
        // try the chosen direction, then the next most likely ones, until one is actually walkable
        var order = Choice == 0 ? new List<int> { 0 } : Enumerable.Range(1, probs.Length - 1).Where(Allowed).OrderByDescending(c => c == Choice ? 9 : probs[c]).Append(0).ToList();
        int prev = Choice;
        foreach (var c in order) {
            if (c == 0) { Choice = 0; Goal = Steer = pos; WantSpeed = 0; Mode = "hold"; return; }
            double a = model.SectorAngle(c) * Math.PI / 180;
            var goal = pos + new Vector2((float)(Math.Cos(a) * model.move_dist), (float)(Math.Sin(a) * model.move_dist));
            var s = Nav.Snap(Nav.Cell(pos.X, pos.Y).Item1, Nav.Cell(pos.X, pos.Y).Item2); var g = Nav.Snap(Nav.Cell(goal.X, goal.Y).Item1, Nav.Cell(goal.X, goal.Y).Item2);
            if (s == null || g == null) continue;
            var gc = Nav.Center(g.Value.Item1, g.Value.Item2); var gv = new Vector2((float)gc.Item1, (float)gc.Item2);
            if (Vector2.Distance(gv, pos) < 70 || Vector2.Dot(Vector2.Normalize(gv - pos), Vector2.Normalize(goal - pos)) < 0.3f) { if (c == prev) blockedUntil[c] = now + 1.5f; continue; }   // wall ahead: that way is not really open; don't bounce back to it right away
            var p = Nav.Path(s.Value, g.Value); if (p == null || p.Count < 3 || p.Count > model.move_dist / Grid.Cell * 3) { if (c == prev) blockedUntil[c] = now + 1.5f; continue; }   // unreachable or a long detour
            var st = Nav.Center(Nav.Steer(p).Item1, Nav.Steer(p).Item2);
            var here = Nav.Cell(pos.X, pos.Y);
            if (!Grid.Get(1, here.Item1, here.Item2) || !Nav.Clear(here, Nav.Steer(p))) st = Nav.Center(p[Math.Min(1, p.Count - 1)].Item1, p[Math.Min(1, p.Count - 1)].Item2);   // hugging a wall: take the next cell first
            Choice = c; Goal = gv; Steer = new Vector2((float)st.Item1, (float)st.Item2); WantSpeed = 215; Mode = "move"; return;
        }
        Choice = 0; Goal = Steer = pos; WantSpeed = 0; Mode = "hold";
    }
}
