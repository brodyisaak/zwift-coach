#!/usr/bin/env python3
"""Week card data for the phone page (feed-style weekly plan).

  python3 tools/week_card.py                # week containing today (config.json "timezone")
  python3 tools/week_card.py --next         # the week after this one (use in the Sunday review)
  python3 tools/week_card.py plans/2026-11-02.json

Writes share/week.json and prints it. The coach routines push it to the phone page
(collection "weeks", doc "current"); see COACH.md "Phone page".
"""
import datetime as dt, glob, json, os, re, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import coach  # noqa: E402

FTP = coach.FTP
TZ = ZoneInfo(coach.CFG.get("timezone", "UTC"))
TODAY = dt.datetime.now(TZ).date()


def pick_plan(args):
    for a in args:
        if a.endswith(".json"):
            return a
    mon = TODAY - dt.timedelta(days=TODAY.weekday())
    if "--next" in args:
        mon += dt.timedelta(days=7)
    return os.path.join(ROOT, "plans", f"{mon.isoformat()}.json")


def segments(steps):
    """Steps -> [[sec, w_start, w_end, free]] with intervals expanded."""
    out = []
    for s in steps:
        k = s[0]
        if k in ("warmup", "cooldown"):
            out.append([s[1], round(s[2]), round(s[3]), 0])
        elif k == "steady":
            out.append([s[1], round(s[2]), round(s[2]), 0])
        elif k == "intervals":
            for _ in range(s[1]):
                out.append([s[2], round(s[3]), round(s[3]), 0])
                out.append([s[4], round(s[5]), round(s[5]), 0])
        elif k == "free":
            out.append([s[1], round(FTP), round(FTP), 1])
    merged = []   # merge identical neighbours to keep the payload small
    for seg in out:
        if merged and merged[-1][1] == merged[-1][2] == seg[1] == seg[2] and merged[-1][3] == seg[3]:
            merged[-1][0] += seg[0]
        else:
            merged.append(seg)
    return merged


def load_metrics(segs):
    w = []
    for sec, a, b, _ in segs:
        for i in range(sec):
            w.append(a + (b - a) * i / max(sec - 1, 1))
    if not w:
        return 0, 0, 0, (0, 0, 0)
    roll = [sum(w[i:i + 30]) / 30 for i in range(0, max(len(w) - 29, 1))]
    np_ = (sum(x ** 4 for x in roll) / len(roll)) ** 0.25
    IF = np_ / FTP
    tss = len(w) / 3600 * IF * IF * 100
    lo = sum(1 for x in w if x < .75 * FTP); hi = sum(1 for x in w if x > 1.05 * FTP)
    return round(sum(w) / len(w)), round(IF, 2), round(tss), (lo, len(w) - lo - hi, hi)


def first(*vals):
    for v in vals:
        if v not in (None, "", []):
            return v
    return None


def result_card(day):
    r = day.get("result") or {}
    if not r:
        return None
    stats = []
    reps = r.get("reps_completed")
    if reps:
        stats.append(["Reps", reps.split(" ")[0]])
    np_ = first(r.get("np"), r.get("np_w"))
    if np_:
        stats.append(["NP", f"{np_} W"])
    elif r.get("avg_w"):
        stats.append(["Avg", f"{r['avg_w']} W"])
    tss = first(r.get("tss"), *[v for k, v in r.items() if k.startswith("tss_at_")])
    if tss:
        stats.append(["TSS", str(tss)])
    hr = first(r.get("last_rep_max_hr"), (r.get("rep_max_hr") or [None])[-1], (r.get("set_max_hr") or [None])[-1], r.get("avg_hr"))
    if hr:
        stats.append(["HR", f"{hr}"])
    stats.append(["RPE", str(r["rpe"]) if r.get("rpe") else "—"])
    verdict = r.get("verdict") or r.get("note") or ""
    verdict = re.split(r"(?<=\.)\s", verdict)[0] if verdict else ""
    return {"stats": stats, "verdict": verdict, "strava_id": first(r.get("strava_id"), (r.get("strava_ids") or [None])[0])}


def latest_text(pattern):
    files = sorted(glob.glob(os.path.join(ROOT, pattern)))
    return (files[-1], open(files[-1]).read()) if files else (None, "")


def readiness():
    path, txt = latest_text("daily/*.md")
    m = re.search(r"Readiness:\s*(\w+)[,.]?\s*([^\n]*)", txt)
    if not m:
        return None
    detail = re.split(r"(?<=\.)\s", m.group(2))
    return {"date": os.path.basename(path)[:10], "status": m.group(1).lower(), "text": " ".join(detail[:2]).strip()}


def verdict():
    path, txt = latest_text("weekly-reviews/*.md")
    m = re.search(r"\*\*Verdict:\s*([^*]+)\*\*\s*([^\n]*)", txt)
    if not m:
        return None
    return {"date": os.path.basename(path)[:10], "headline": m.group(1).strip().rstrip("."), "text": m.group(2).strip()}


def next_gate():
    """Next FTP gate from config.json "gates" ([{"date", "ftp"}]) plus the goal itself."""
    gates = [(dt.date.fromisoformat(g["date"]), int(g["ftp"])) for g in coach.CFG.get("gates", [])]
    if coach.CFG.get("goal_date"):
        gates.append((dt.date.fromisoformat(coach.CFG["goal_date"]), int(CFG_GOAL)))
    gates = sorted(g for g in gates if g[0] >= TODAY)
    if not gates:
        return None
    d, w = gates[0]
    return {"date": d.isoformat(), "label": d.strftime("%b %-d"), "target": w, "to_go": w - FTP, "days": (d - TODAY).days}


CFG_GOAL = coach.CFG.get("goal_ftp", 330)


def main(args):
    path = pick_plan(args)
    plan = coach.load_plan(path)
    days, tot_min, tot_tss, split = [], 0, 0, [0, 0, 0]
    for d in plan["days"]:
        date = dt.date.fromisoformat(d["date"])
        title, desc, steps = coach.render_day(d)
        kind = "rest" if d["session"] == "rest" else ("key" if d["session"] in coach.KEY_SESSIONS else
                                                     "recovery" if d["session"] == "recovery" else "endurance")
        if d["session"] == "ftp_test":
            kind = "test"
        segs = [] if kind == "rest" else segments(steps)
        avg_w, IF, tss, sp = load_metrics(segs)
        minutes = 0 if kind == "rest" else coach.duration_min(steps)
        optional = "optional" in (d.get("note", "") + d.get("status", "")).lower()
        res = result_card(d)
        done = bool(res) or d.get("status") == "done"
        status = ("done" if done else "today" if date == TODAY else
                  "past" if date < TODAY else "planned")
        tag = d.get("status", "planned")
        if kind != "rest":
            tot_min += minutes; tot_tss += tss
            split = [a + b for a, b in zip(split, sp)]
        days.append({
            "date": d["date"], "dow": date.strftime("%a"), "label": date.strftime("%a %b %-d"),
            "title": title.replace(f"{date.strftime('%a %b %-d')} · ", ""), "kind": kind, "optional": optional,
            "status": status, "plan_status": tag if tag not in ("planned", "done") else "",
            "minutes": minutes, "avg_w": avg_w, "if": IF, "tss": tss, "desc": desc,
            "note": d.get("note", ""), "profile": segs, "result": res,
        })
    s = sum(split) or 1
    keys = [x for x in days if x["kind"] in ("key", "test")]
    ws = dt.date.fromisoformat(plan["week_start"])
    data = {
        "updated": dt.datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"),
        "today": TODAY.isoformat(),
        "week_start": plan["week_start"], "week_end": (ws + dt.timedelta(days=6)).isoformat(),
        "range": f"{ws.strftime('%b %-d')} – {(ws + dt.timedelta(days=6)).strftime('%b %-d')}",
        "block": plan.get("block", ""), "target_hours": plan.get("target_hours"),
        "strength": plan.get("strength", ""),
        "ftp": FTP, "weight_kg": coach.CFG.get("weight_kg"), "goal_ftp": CFG_GOAL,
        "goal_label": dt.date.fromisoformat(coach.CFG["goal_date"]).strftime("%b %-d") if coach.CFG.get("goal_date") else "",
        "zones": [round(p * FTP) for p in (.55, .75, .90, 1.05, 1.20, 1.50)],
        "totals": {"minutes": tot_min, "tss": tot_tss, "key_planned": len(keys),
                   "key_done": sum(1 for x in keys if x["status"] == "done"),
                   "rides": sum(1 for x in days if x["kind"] != "rest")},
        "split": {"low": round(100 * split[0] / s), "mod": round(100 * split[1] / s), "high": round(100 * split[2] / s),
                  "target": [78, 16, 6] if ws < dt.date.fromisoformat(coach.CFG.get("polarized_from", "2100-01-01")) else [80, 10, 10]},
        "gate": next_gate(), "readiness": readiness(), "verdict": verdict(),
        "days": days,
    }
    out = os.path.join(ROOT, "share", "week.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(data, open(out, "w"), separators=(",", ":"), ensure_ascii=False)
    print(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
