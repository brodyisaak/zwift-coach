"""Compute ride metrics from a Strava get_activity_streams JSON file.
Usage: python3 ride_metrics.py streams.json [FTP]
Prints: hours recorded, avg W, NP, IF, TSS, VI, power-zone minutes (Coggan 7),
Z5+ minutes, best 1/5/20/60-min power, avg/max HR, HR in best 5- and 20-min windows.
"""
import json, sys
import numpy as np

def to1hz(t, x, maxgap=5):
    t = np.asarray(t); x = np.asarray(x, dtype=float)
    n = int(t[-1]) + 1; out = np.zeros(n); valid = np.zeros(n, bool)
    for i in range(len(t) - 1):
        a, b = int(t[i]), int(t[i + 1])
        if b - a <= maxgap:
            out[a:b] = x[i]; valid[a:b] = True
    out[-1] = x[-1]; valid[-1] = True
    return out, valid

def best(w, s):
    if len(w) < s: return None, None
    c = np.cumsum(np.insert(w, 0, 0)); m = (c[s:] - c[:-s]) / s; i = int(m.argmax())
    return float(m[i]), i

def main(path, ftp=280):
    d = json.load(open(path)); t = d["time"]
    # Coggan 7-zone, Strava-style boundaries (FTP 280 -> 155/211/253/295/337/421 W)
    lo = [0] + [int(p * ftp) + 1 for p in (.55, .75, .90, 1.05, 1.20, 1.50)]
    res = {}
    h = None
    if d.get("heart_rate"):
        h, hv = to1hz(t, d["heart_rate"]); res["avg_hr"] = round(h[hv].mean()); res["max_hr"] = int(h.max())
    if d.get("watts"):
        w, v = to1hz(t, [x or 0 for x in d["watts"]]); wv = w[v]
        roll = np.convolve(wv, np.ones(30) / 30, "valid"); np_ = float(np.mean(roll ** 4) ** 0.25)
        hrs = v.sum() / 3600; IF = np_ / ftp
        res.update(hours=round(hrs, 2), avg_w=round(wv.mean()), np=round(np_), IF=round(IF, 2),
                   tss=round(hrs * IF * IF * 100), vi=round(np_ / wv.mean(), 2))
        zm = []
        for i, a in enumerate(lo):
            b = lo[i + 1] if i + 1 < len(lo) else 1e9
            zm.append(round(((wv >= a) & (wv < b)).sum() / 60))
        res["zone_min_Z1_Z7"] = zm; res["z5plus_min"] = sum(zm[4:])
        for name, s in [("best_1min", 60), ("best_5min", 300), ("best_20min", 1200), ("best_60min", 3600)]:
            p, i = best(w, s); res[name] = round(p) if p else None
            if p and h is not None and s in (300, 1200):
                res[name + "_avg_hr"] = round(h[i:i + s].mean())
    print(json.dumps(res, indent=1))

if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 280)
