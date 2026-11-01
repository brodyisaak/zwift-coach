#!/usr/bin/env python3
"""Calendar blocks for a plan week (Google Calendar; calendar id in config.json).

  python3 tools/calendar_blocks.py plans/2026-11-02.json

Prints JSON: one block per ride day (rest days get none). Each block has a unique marker
"coach-block:<date>" in its description so the routines can find, update or remove it.
Times are local (config.json "timezone"), no offset. Rules live in config.json "calendar".
"""
import datetime as dt, json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import coach  # noqa: E402

C = coach.CFG["calendar"]
hm = lambda s: dt.timedelta(hours=int(s[:2]), minutes=int(s[3:5]))


def wed_start(date):
    if date.isoformat() in C.get("wed_overrides", {}):
        return C["wed_overrides"][date.isoformat()], "override"
    anchor = dt.date.fromisoformat(C["week_a_anchor_monday"])
    weeks = ((date - dt.timedelta(days=date.weekday())) - anchor).days // 7
    return (C["wed_week_a_start"], "week A") if weeks % 2 == 0 else (C["wed_week_b_start"], "week B")


def blocks(plan_path):
    plan = coach.load_plan(plan_path)
    out = []
    for d in plan["days"]:
        if d["session"] == "rest":
            continue
        date = dt.date.fromisoformat(d["date"])
        title, desc, steps = coach.render_day(d)
        mins = coach.duration_min(steps)
        r = C.get("round_min", 15)
        block = math.ceil(mins / r) * r
        wd = date.weekday()
        why = "weekday"
        if d.get("calendar_start"):                       # per-day override in the plan
            start, why = hm(d["calendar_start"]), "plan override"
        elif wd == 2:
            s, why = wed_start(date); start = hm(s)
        elif wd >= 5:
            start = hm(C["weekend_finish_by"]) - dt.timedelta(minutes=block)
            start = max(hm(C["weekend_earliest_start"]), min(hm(C["weekend_latest_start"]), start))
            start = dt.timedelta(minutes=(start.seconds // 60) // r * r)
            why = "weekend"
        else:
            start = hm(C["weekday_start"])
        t0 = dt.datetime.combine(date, dt.time()) + start
        t1 = t0 + dt.timedelta(minutes=block)
        key = d["session"] in coach.KEY_SESSIONS
        optional = "optional" in (d.get("note", "") + d.get("status", "")).lower()
        slot = f"COACH_{wd + 1}_{coach.DAYS[wd]}"
        summary = f"Zwift · {title.split(' · ')[-1]}" + (" (optional)" if optional else "")
        out.append({
            "date": d["date"], "start": t0.strftime("%Y-%m-%dT%H:%M:%S"), "end": t1.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary": summary, "key": key, "optional": optional, "rule": why,
            "availability": "AVAILABILITY_FREE" if optional else "AVAILABILITY_BUSY",
            "colorId": "6" if key else ("8" if optional else "7"),
            "description": (f"{'Key session. ' if key else ''}{desc}\n\n"
                            f"Zwift: Workouts > Custom Workouts > {slot} ({mins} min). Restart Zwift if it isn't there.\n"
                            + (f"Coach note: {d['note']}\n" if d.get("note") else "")
                            + f"\nAdded by the training coach. {C['marker']}:{d['date']}"),
        })
    return out


if __name__ == "__main__":
    print(json.dumps({"calendar_id": C["calendar_id"], "blocks": blocks(sys.argv[1])}, indent=1, ensure_ascii=False))
