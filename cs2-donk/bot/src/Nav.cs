namespace DonkAI;

// A* over the walkable grid learned from demos, plus straight-line shortcuts ("string pulling").
public static class Nav {
    public static (int, int) Cell(double x, double y) => ((int)((x - Grid.X0) / Grid.Cell), (int)((y - Grid.Y0) / Grid.Cell));
    public static (double, double) Center(int cx, int cy) => (Grid.X0 + (cx + .5) * Grid.Cell, Grid.Y0 + (cy + .5) * Grid.Cell);
    public static (int, int)? Snap(int cx, int cy, int maxR = 20) {
        if (Grid.Get(1, cx, cy)) return (cx, cy);
        for (int r = 1; r <= maxR; r++)
            for (int dx = -r; dx <= r; dx++) for (int dy = -r; dy <= r; dy++)
                if (Math.Max(Math.Abs(dx), Math.Abs(dy)) == r && Grid.Get(1, cx + dx, cy + dy)) return (cx + dx, cy + dy);
        return null;
    }
    static readonly (int, int, double)[] Dirs = { (1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414) };
    public static List<(int, int)>? Path((int, int) s, (int, int) g, int budget = 40000) {
        if (s == g) return new() { g };
        var open = new PriorityQueue<(int, int), double>(); var came = new Dictionary<(int, int), (int, int)>(); var cost = new Dictionary<(int, int), double> { [s] = 0 };
        double H((int, int) a) => Math.Sqrt((a.Item1 - g.Item1) * (a.Item1 - g.Item1) + (a.Item2 - g.Item2) * (a.Item2 - g.Item2));
        open.Enqueue(s, H(s)); int n = 0;
        while (open.Count > 0 && n++ < budget) {
            var c = open.Dequeue(); if (c == g) break;
            foreach (var (dx, dy, w) in Dirs) {
                var nb = (c.Item1 + dx, c.Item2 + dy); if (!Grid.Get(1, nb.Item1, nb.Item2)) continue;
                if (dx != 0 && dy != 0 && (!Grid.Get(1, c.Item1 + dx, c.Item2) || !Grid.Get(1, c.Item1, c.Item2 + dy))) continue;   // no corner cutting
                double nc = cost[c] + w; if (cost.TryGetValue(nb, out var old) && old <= nc) continue;
                cost[nb] = nc; came[nb] = c; open.Enqueue(nb, nc + H(nb));
            }
        }
        if (!came.ContainsKey(g)) return null;
        var p = new List<(int, int)> { g }; var k = g; while (k != s) { k = came[k]; p.Add(k); } p.Reverse(); return p;
    }
    public static bool Clear((int, int) a, (int, int) b) {
        int n = Math.Max(Math.Abs(b.Item1 - a.Item1), Math.Abs(b.Item2 - a.Item2)) * 2 + 1;
        for (int i = 0; i <= n; i++) { double t = (double)i / n; if (!Grid.Get(1, (int)Math.Round(a.Item1 + (b.Item1 - a.Item1) * t), (int)Math.Round(a.Item2 + (b.Item2 - a.Item2) * t))) return false; }
        return true;
    }
    // furthest waypoint reachable in a straight line from the start
    public static (int, int) Steer(List<(int, int)> p) { var best = p[Math.Min(1, p.Count - 1)]; for (int i = 2; i < p.Count && i < 60; i++) if (Clear(p[0], p[i])) best = p[i]; return best; }
}
