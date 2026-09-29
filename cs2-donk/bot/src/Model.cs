using System.Text.Json;
namespace DonkAI;

// Gradient-boosted trees exported from LightGBM (see deploy_model.py); predicts where the player will be in 2 s.
public sealed class Tree {
    public int root { get; set; }
    public int[] f { get; set; } = []; public double[] t { get; set; } = []; public int[] l { get; set; } = []; public int[] r { get; set; } = []; public int[] d { get; set; } = []; public double[] v { get; set; } = [];
    public double Eval(double[] x) {
        int n = root;
        while (n >= 0) { double a = x[f[n]]; n = double.IsNaN(a) ? (d[n] == 1 ? l[n] : r[n]) : (a <= t[n] ? l[n] : r[n]); }
        return v[~n];
    }
}
public sealed class GoalModel {
    public string[] features { get; set; } = [];
    public int classes { get; set; }
    public int sectors { get; set; }
    public int move_dist { get; set; }
    public Tree[] trees { get; set; } = [];
    public static GoalModel Load(string path) => JsonSerializer.Deserialize<GoalModel>(File.ReadAllText(path))!;
    // class 0 = hold position, class k = move toward sector k (k-1) * 360/sectors degrees
    public double[] Probs(double[] x) {
        var z = new double[classes];
        for (int i = 0; i < trees.Length; i++) z[i % classes] += trees[i].Eval(x);
        double m = z.Max(), s = 0; for (int c = 0; c < classes; c++) { z[c] = Math.Exp(z[c] - m); s += z[c]; }
        for (int c = 0; c < classes; c++) z[c] /= s; return z;
    }
    public double SectorAngle(int c) => (c - 1) * 360.0 / sectors;
}

// Where donk keeps his crosshair: 36 yaw sectors (10 degrees each) + pitch regression.
public sealed class LookModel {
    public string[] features { get; set; } = [];
    public int classes { get; set; }
    public Tree[] trees { get; set; } = [];
    public Tree[] pitch { get; set; } = [];
    public static LookModel Load(string path) => JsonSerializer.Deserialize<LookModel>(File.ReadAllText(path))!;
    public double[] Probs(double[] x) {
        var z = new double[classes];
        for (int i = 0; i < trees.Length; i++) z[i % classes] += trees[i].Eval(x);
        double m = z.Max(), s = 0; for (int c = 0; c < classes; c++) { z[c] = Math.Exp(z[c] - m); s += z[c]; }
        for (int c = 0; c < classes; c++) z[c] /= s; return z;
    }
    public double Pitch(double[] x) { double s = 0; foreach (var t in pitch) s += t.Eval(x); return s; }
    // circular mean around the best sector, in degrees (-180..180]
    public double Yaw(double[] p) {
        int b = Array.IndexOf(p, p.Max()); double sx = 0, sy = 0;
        for (int k = -1; k <= 1; k++) { int c = (b + k + classes) % classes; double a = c * 360.0 / classes * Math.PI / 180; sx += p[c] * Math.Cos(a); sy += p[c] * Math.Sin(a); }
        return Math.Atan2(sy, sx) * 180 / Math.PI;
    }
}
