#!/usr/bin/env python3
"""Training engine: Zwift workout builder, readiness check, daily pivot.

Pure standard library. Run from the training folder:

  python3 tools/coach.py build plans/2026-10-19.json         # write the week's .zwo files to Zwift
  python3 tools/coach.py readiness [YYYY-MM-DD]               # readiness from health/daily.csv
  python3 tools/coach.py pivot plans/2026-10-19.json [DATE]   # apply readiness to DATE's session, rebuild
  python3 tools/coach.py show plans/2026-10-19.json           # print the week in watts

Plan file = one Mon-Sun week. Each day: {"date", "session": <library key>, "params": {...}, "status"}.
Watts are prescribed from config.json FTP. Zwift .zwo files store % of Zwift's FTP, so Zwift's
FTP setting must equal config.json "ftp" (check in Zwift: Menu > Settings > Profile).
"""
import csv, datetime as dt, json, math, os, statistics, sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cfg = os.path.join(ROOT, "config.json")
CFG = json.load(open(_cfg if os.path.exists(_cfg) else os.path.join(ROOT, "config.example.json")))
FTP = CFG["ftp"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
REST_REQUIRED = set(CFG.get("rest_days", {}).get("required", ["Fri"]))   # always rest, never a moved session
REST_OPTIONAL = set(CFG.get("rest_days", {}).get("optional", ["Sat"]))   # easy/optional; last-resort slot only


def weekday(date_str):
    return DAYS[dt.date.fromisoformat(date_str).weekday()]


# ---------------------------------------------------------------- workout library
# Each builder returns (title, description, steps). Steps are tuples:
#   ("warmup", sec, lo_w, hi_w) ("cooldown", sec, hi_w, lo_w) ("steady", sec, w)
#   ("intervals", reps, on_sec, on_w, off_sec, off_w) ("free", sec, label)
def _wu(extra=True):
    s = [("warmup", 600, 0.50 * FTP, 0.75 * FTP)]
    if extra:
        s += [("intervals", 2, 60, 1.07 * FTP, 60, 0.55 * FTP), ("steady", 180, 0.55 * FTP)]
    return s

def _cd(sec=600):
    return [("cooldown", sec, 0.60 * FTP, 0.45 * FTP)]

def ftp_test(p):
    steps = _wu() + [("free", 300, "5-min ALL OUT (ERG off). Start ~360 W, hold"),
                     ("steady", 600, 0.50 * FTP),
                     ("free", 1200, "20-min ALL OUT (ERG off). 0-5 min @ 280 W, +5 W every 3 min if HR <165, empty the tank last 3 min")] + _cd()
    return ("FTP test 20-min", "5-min benchmark + 20-min test. New FTP = 95% of 20-min avg.", steps)

def vo2_long(p):  # 4-5 min reps
    reps, on, pct = p.get("reps", 5), p.get("on_sec", 240), p.get("pct", 1.13)
    steps = _wu() + [("intervals", reps, on, pct * FTP, p.get("off_sec", on), 0.50 * FTP)] + _cd()
    return (f"VO2 {reps}x{on//60}min @ {round(pct*FTP)}W", f"{reps} x {on//60} min @ {round(pct*FTP)} W, equal recovery @ {round(.5*FTP)} W. Cadence 90-100.", steps)

def vo2_3015(p):
    sets, reps, pct = p.get("sets", 3), p.get("reps", 10), p.get("pct", 1.25)
    steps = _wu()
    for i in range(sets):
        steps.append(("intervals", reps, 30, pct * FTP, 15, 0.50 * FTP))
        if i < sets - 1:
            steps.append(("steady", 300, 0.50 * FTP))
    steps += _cd()
    return (f"30/15s {sets}x{reps} @ {round(pct*FTP)}W", f"{sets} sets of {reps} x (30 s @ {round(pct*FTP)} W / 15 s @ {round(.5*FTP)} W), 5 min easy between sets.", steps)

def threshold(p):  # e.g. 2x20 @ 95%
    reps, on, pct, off = p.get("reps", 2), p.get("on_sec", 1200), p.get("pct", 0.95), p.get("off_sec", 300)
    steps = _wu() + [("intervals", reps, on, pct * FTP, off, 0.55 * FTP)] + _cd()
    return (f"Threshold {reps}x{on//60} @ {round(pct*FTP)}W", f"{reps} x {on//60} min @ {round(pct*FTP)} W, {off//60} min easy between.", steps)

def over_under(p):
    reps, blocks = p.get("reps", 3), p.get("blocks", 4)
    under, over = p.get("under", 0.92), p.get("over", 1.05)
    steps = _wu()
    for i in range(reps):
        steps.append(("intervals", blocks, 120, under * FTP, 60, over * FTP))
        if i < reps - 1:
            steps.append(("steady", 300, 0.55 * FTP))
    steps += _cd()
    return (f"Over-unders {reps}x{blocks*3}min", f"{reps} sets of {blocks} x (2 min @ {round(under*FTP)} W / 1 min @ {round(over*FTP)} W), 5 min easy between.", steps)

def sweet_spot(p):
    reps, on, pct = p.get("reps", 3), p.get("on_sec", 900), p.get("pct", 0.90)
    steps = _wu(False) + [("intervals", reps, on, pct * FTP, 300, 0.55 * FTP)] + _cd()
    return (f"Sweet spot {reps}x{on//60} @ {round(pct*FTP)}W", f"{reps} x {on//60} min @ {round(pct*FTP)} W, 5 min easy between.", steps)

# Z2 formats rotate so endurance days never look the same. All stay in Z2 on average (IF ~0.65-0.70);
# only "sprinkles" leaves Z2, for 10 s at a time. Cadence targets and on-screen cues are shown by Zwift.
Z2_STYLES = ["ladder", "hills", "sprinkles", "pyramid"]
Z2_NAMES = {"ladder": "Cadence ladder", "hills": "Rolling hills", "sprinkles": "Z2 + sprint sprinkles",
            "pyramid": "Z2 pyramid", "steady": "Steady Z2"}

def _z2_cycle(style, pct):
    W = lambda x: x * FTP
    if style == "ladder":      # 10-min cycle: same power feel, cadence climbs, then a spin-out
        return [("steady", 240, W(pct), {"cadence": 85, "text": "Ladder: 85 rpm, settle in"}),
                ("steady", 180, W(pct + 0.02), {"cadence": 95, "text": "95 rpm, smooth circles"}),
                ("steady", 120, W(pct - 0.03), {"cadence": 105, "text": "105 rpm, quiet upper body"}),
                ("steady", 60, W(pct - 0.08), {"cadence": 115, "text": "Spin-out 115+ rpm, no bouncing"})]
    if style == "hills":       # 7-min cycle: seated low-cadence climb, then a spinny descent
        return [("steady", 240, W(min(pct + 0.06, 0.75)), {"cadence": 70, "text": "Climb: seated, 70 rpm, push through the whole stroke"}),
                ("steady", 180, W(pct - 0.06), {"cadence": 95, "text": "Descent: 95 rpm, loosen shoulders"})]
    if style == "sprinkles":   # 8-min cycle with one 10-s acceleration
        return [("steady", 400, W(pct), {"text": "Cruise Z2, drink"}),
                ("steady", 10, W(1.50), {"cadence": 110, "text": "Sprinkle: 10 s fast, seated, spin it up"}),
                ("steady", 70, W(pct - 0.10), {"text": "Easy, back to Z2"})]
    if style == "pyramid":     # 18-min cycle: climb up and back down through Z2
        steps = [0.62, 0.66, 0.70, 0.74, 0.70, 0.66]
        cad = [90, 85, 95, 80, 100, 90]
        return [("steady", 180, W(x), {"cadence": c, "text": f"Step {i+1}/6: {round(W(x))} W @ {c} rpm"})
                for i, (x, c) in enumerate(zip(steps, cad))]
    return [("steady", 600, W(pct), {})]

def endurance(p):
    mins, pct = p.get("minutes", 60), p.get("pct", 0.70)
    style = p.get("style", "steady")
    body = max(mins * 60 - 900, 600)
    cycle = _z2_cycle(style, pct)
    steps, t, last_fuel = [("warmup", 600, 0.50 * FTP, pct * FTP, {"text": f"{Z2_NAMES[style]} today. Easy first 10 min"})], 0, 0
    while t < body:
        for st in cycle:
            if t >= body:
                break
            sec = min(st[1], body - t)
            extra = dict(st[3])
            fe = p.get("fuel_every_min", 20)   # fuel cue every ~20 min on long rides (15 after high HR drift)
            if mins >= 90 and t - last_fuel >= fe * 60:
                extra["text"] = (extra.get("text", "") + (" | Eat ~20 g carbs + drink" if fe <= 15 else " | Eat 25-30 g carbs")).strip(" |"); last_fuel = t
            steps.append(("steady", sec, st[2], extra)); t += sec
    late = p.get("late_efforts")      # durability: quality work on tired legs near the end of a long ride
    if late:
        r, m, lp = late.get("reps", 2), late.get("min", 10), late.get("pct", 0.89)
        cut = r * m * 60 + (r - 1) * 300
        while steps and cut > 0:          # take the time from the end of the Z2 body
            last = steps[-1]
            if last[0] != "steady" or last[1] > cut:
                steps[-1] = (last[0], last[1] - cut) + tuple(last[2:]); cut = 0
            else:
                steps.pop(); cut -= last[1]
        for i in range(r):
            steps.append(("steady", m * 60, lp * FTP, {"cadence": 90, "text": f"Late effort {i+1}/{r}: {m} min @ {round(lp*FTP)} W on tired legs. Fuel first"}))
            if i < r - 1:
                steps.append(("steady", 300, 0.60 * FTP, {"text": "Easy 5 min"}))
    sprints = p.get("finish_sprints")  # small anaerobic dose at the end of an easy ride
    if sprints:
        n, sec = sprints.get("reps", 5), sprints.get("sec", 20)
        for i in range(n):
            steps.append(("steady", sec, 1.70 * FTP, {"cadence": 105, "text": f"Sprint {i+1}/{n}: {sec} s hard, seated 10 s then stand"}))
            steps.append(("steady", 160, 0.50 * FTP, {"text": "Spin easy"}))
    steps.append(("cooldown", 300, pct * FTP, 0.50 * FTP, {"text": "Cool-down. Good work"}))
    desc = {"ladder": "Z2 with a cadence ladder every 10 min (85-95-105-115 rpm).",
            "hills": "Z2 rolling hills: 4 min seated at 70 rpm near the top of Z2, 3 min spinning at 95.",
            "sprinkles": "Z2 with a 10-s acceleration every 8 min. Keeps the legs snappy.",
            "pyramid": "Z2 pyramid: 3-min steps up and down through Z2 with changing cadence.",
            "steady": "Steady Z2."}[style]
    if late:
        desc += f" Finishes with {late.get('reps',2)} x {late.get('min',10)} min @ {round(late.get('pct',0.89)*FTP)} W (durability)."
    if sprints:
        desc += f" Ends with {sprints.get('reps',5)} x {sprints.get('sec',20)} s sprints (anaerobic dose)."
    return (f"{Z2_NAMES[style]} {mins}min @ ~{round(pct*FTP)}W",
            f"{desc} Avg ~{round(pct*FTP)} W, cap {round(0.76*FTP)} W outside sprinkles. Follow the on-screen cues."
            + (" Fuel 60-80 g carbs/h." if mins >= 90 else ""), steps)

def recovery(p):
    mins = p.get("minutes", 40)
    steps = [("warmup", 300, 0.40 * FTP, 0.50 * FTP), ("steady", mins * 60 - 600, 0.50 * FTP), ("cooldown", 300, 0.50 * FTP, 0.40 * FTP)]
    return (f"Recovery spin {mins}min", f"{mins} min @ ≤{round(.55*FTP)} W. Legs only, no efforts.", steps)

def openers(p):
    on = p.get("on_sec", 180); off = p.get("off_sec", 180); pct = p.get("pct", 1.07); z2 = p.get("z2_min", 0)
    steps = [("warmup", 600, 0.50 * FTP, 0.70 * FTP)]
    if z2:
        steps += [("steady", z2 * 60, 0.65 * FTP)]
    steps += [("intervals", p.get("reps", 3), on, pct * FTP, off, 0.50 * FTP),
              ("intervals", 3, 15, 1.60 * FTP, 105, 0.50 * FTP)] + _cd(420)
    on_txt = f"{on // 60} min" if on % 60 == 0 else f"{on} s"
    return ("Openers", f"{p.get('reps', 3)} x {on_txt} @ {round(pct*FTP)} W, 3 x 15 s hard. Stay fresh.", steps)

def rest(p):
    return ("Rest day", "Off the bike, or commute only.", [("steady", 600, 0.45 * FTP)])

LIB = {"ftp_test": ftp_test, "vo2_long": vo2_long, "vo2_3015": vo2_3015, "threshold": threshold,
       "over_under": over_under, "sweet_spot": sweet_spot, "endurance": endurance, "recovery": recovery,
       "openers": openers, "rest": rest}
KEY_SESSIONS = {"ftp_test", "vo2_long", "vo2_3015", "threshold", "over_under", "sweet_spot"}
DEFAULT_PCT = {"vo2_long": 1.13, "threshold": 0.95, "sweet_spot": 0.90}   # must match the builders above


# ---------------------------------------------------------------- .zwo writer
def zwo_xml(name, desc, steps):
    f = lambda w: f"{w / FTP:.3f}"
    out = ['<workout_file>', '  <author>zwift-coach</author>', f'  <name>{escape(name)}</name>',
           f'  <description>{escape(desc)}</description>', '  <sportType>bike</sportType>',
           '  <tags><tag name="COACH"/></tags>', '  <workout>']
    def emit(tag, attrs, extra):
        cad = f' Cadence="{extra["cadence"]}"' if extra.get("cadence") else ""
        if extra.get("text"):
            out.append(f'    <{tag} {attrs}{cad}>')
            out.append(f'      <textevent timeoffset="0" message="{escape(extra["text"], {chr(34): "&quot;"})}"/>')
            out.append(f'    </{tag}>')
        else:
            out.append(f'    <{tag} {attrs}{cad}/>')
    for s in steps:
        k = s[0]
        if k == "warmup":
            emit("Warmup", f'Duration="{s[1]}" PowerLow="{f(s[2])}" PowerHigh="{f(s[3])}"', s[4] if len(s) > 4 else {})
        elif k == "cooldown":
            emit("Cooldown", f'Duration="{s[1]}" PowerLow="{f(s[2])}" PowerHigh="{f(s[3])}"', s[4] if len(s) > 4 else {})
        elif k == "steady":
            emit("SteadyState", f'Duration="{s[1]}" Power="{f(s[2])}"', s[3] if len(s) > 3 else {})
        elif k == "intervals":
            out.append(f'    <IntervalsT Repeat="{s[1]}" OnDuration="{s[2]}" OffDuration="{s[4]}" OnPower="{f(s[3])}" OffPower="{f(s[5])}"/>')
        elif k == "free":
            out.append(f'    <FreeRide Duration="{s[1]}" FlatRoad="1">')
            out.append(f'      <textevent timeoffset="0" message="{escape(s[2])}"/>')
            out.append('    </FreeRide>')
    out += ['  </workout>', '</workout_file>', '']
    return "\n".join(out)

def duration_min(steps):
    tot = 0
    for s in steps:
        tot += s[1] * (s[2] + s[4]) if s[0] == "intervals" else s[1]
    return round(tot / 60)

def zwift_dir():
    d = os.path.expanduser(CFG["zwift_workouts_dir"])
    # remote shells may mount ~/Documents/Zwift at ~/mnt/Zwift; support both
    alt = os.path.expanduser("~/mnt/Zwift/Workouts/" + str(CFG["zwift_id"]))
    return d if os.path.isdir(d) else alt


# ---------------------------------------------------------------- commands
def load_plan(path):
    return json.load(open(path))

def save_plan(path, plan):
    json.dump(plan, open(path, "w"), indent=2)

def render_day(day):
    title, desc, steps = LIB[day["session"]](day.get("params", {}))
    return title, desc, steps

def _enforce_rest_days(plan_path):
    """Required rest days (Friday) are always rest: anything else scheduled there is reset with a note."""
    plan = load_plan(plan_path); changed = False
    for d in plan["days"]:
        if weekday(d["date"]) in REST_REQUIRED and d["session"] != "rest":
            print(f"WARNING: {d['date']} ({weekday(d['date'])}) is a required rest day; {d['session']} removed.")
            d.update(original=dict(session=d["session"], params=d.get("params", {})), session="rest", params={},
                     note="Required rest day (Friday).")
            changed = True
    if changed:
        save_plan(plan_path, plan)


def build(plan_path, only_date=None):
    _enforce_rest_days(plan_path)
    plan = load_plan(plan_path)
    zdir = zwift_dir()
    arch = os.path.join(ROOT, "zwift-workouts", os.path.basename(plan_path).replace(".json", ""))
    os.makedirs(arch, exist_ok=True)
    for day in plan["days"]:
        if only_date and day["date"] != only_date:
            continue
        d = dt.date.fromisoformat(day["date"])
        wd = DAYS[d.weekday()]
        if day["session"] == "endurance" and "style" not in day.get("params", {}):
            nxt = next((x for x in plan["days"] if x["date"] > day["date"]), None)
            opts = [z for z in Z2_STYLES if not (z == "sprinkles" and ((nxt and nxt["session"] in KEY_SESSIONS) or day.get("params", {}).get("minutes", 60) >= 90))]
            day.setdefault("params", {})["style"] = opts[d.toordinal() % len(opts)]
            save_plan(plan_path, plan)
        title, desc, steps = render_day(day)
        name = f"{wd} {d.strftime('%b %-d')} · {title}"
        if day.get("status") and day["status"] != "planned":
            desc = f"[{day['status'].upper()}] " + desc
        xml = zwo_xml(name, desc + (" " + day["note"] if day.get("note") else ""), steps)
        fn = f"COACH_{d.weekday()+1}_{wd}.zwo"  # fixed slot per weekday: overwritten each week
        for folder in (zdir, arch):
            if folder and os.path.isdir(folder):
                open(os.path.join(folder, fn), "w").write(xml)
        print(f"{day['date']} {wd}: {name} ({duration_min(steps)} min) -> {fn}")
    print(f"Zwift folder: {zdir}  (restart Zwift to load changes; Workouts > Custom Workouts)")

def show(plan_path):
    plan = load_plan(plan_path)
    for day in plan["days"]:
        t, desc, steps = render_day(day)
        print(f"{day['date']} {DAYS[dt.date.fromisoformat(day['date']).weekday()]}: {t} — {desc} [{duration_min(steps)} min] {day.get('status','planned')}")


# ---------------------------------------------------------------- readiness
def read_health():
    p = os.path.join(ROOT, "health", "daily.csv")
    if not os.path.exists(p):
        return []
    rows = []
    for r in csv.DictReader(open(p)):
        rows.append({k: (float(v) if v not in ("", None) and k != "date" else (v or None)) for k, v in r.items()})
    return sorted(rows, key=lambda r: r["date"])

def readiness(date=None):
    rows = read_health()
    date = date or dt.date.today().isoformat()
    today = next((r for r in rows if r["date"] == date), None)
    hist = [r for r in rows if r["date"] < date][-28:]
    res = {"date": date, "status": "unknown", "flags": [], "notes": []}
    if not today or len(hist) < 7:
        res["notes"].append("Not enough Apple Health data (need today + 7 prior days). Plan stands as written.")
        return res
    def base(key, log=False):
        v = [math.log(r[key]) if log else r[key] for r in hist if r.get(key)]
        return (statistics.mean(v), statistics.pstdev(v) or 1e-6) if len(v) >= 7 else (None, None)
    red, amber = [], []
    if today.get("hrv"):
        m, sd = base("hrv", log=True)
        if m is not None:
            # use 3-day rolling ln(HRV) to damp single-night noise
            recent = [math.log(r["hrv"]) for r in (hist[-2:] + [today]) if r.get("hrv")]
            z = (statistics.mean(recent) - m) / sd
            res["hrv_z"] = round(z, 2)
            if z < -2: red.append(f"HRV well below normal (z {z:.1f})")
            elif z < -1: amber.append(f"HRV below normal (z {z:.1f})")
    if today.get("rhr"):
        m, _ = base("rhr")
        if m is not None:
            d = today["rhr"] - m
            res["rhr_delta"] = round(d, 1)
            prev = hist[-1].get("rhr")
            if d > 5 and prev and prev - m > 5: red.append(f"Resting HR +{d:.0f} bpm two days running")
            elif d > 3: amber.append(f"Resting HR +{d:.0f} bpm")
    if today.get("sleep_h") is not None:
        s = today["sleep_h"]
        if s < 5.5: red.append(f"Short sleep ({s:.1f} h)")
        elif s < 6.5: amber.append(f"Sleep {s:.1f} h")
    if today.get("resp_rate"):
        m, _ = base("resp_rate")
        if m is not None and today["resp_rate"] - m > 1.5:
            red.append(f"Respiratory rate +{today['resp_rate']-m:.1f} — possible illness")
    if len(amber) >= 2:
        red.append("Multiple amber flags")
    res["flags"] = red + amber
    res["status"] = "red" if red else "amber" if amber else "green"
    return res

def pivot(plan_path, date=None):
    date = date or dt.date.today().isoformat()
    plan = load_plan(plan_path)
    r = readiness(date)
    day = next((d for d in plan["days"] if d["date"] == date), None)
    print(json.dumps(r, indent=1))
    if not day or r["status"] in ("unknown", "green"):
        print("No change." if day else "Date not in plan.")
        return r
    if day.get("status") == "red-swapped":
        print("Already swapped for a recovery day. No change.")
        return r
    # re-runs start from the original session, so trims never stack (amber can still escalate to red)
    if day.get("status") == "amber-adjusted":
        orig = day["original"]
    else:
        orig = dict(session=day["session"], params=dict(day.get("params", {})))
    key, p = orig["session"], dict(orig["params"])
    if r["status"] == "amber":
        if key in ("vo2_long", "threshold", "sweet_spot"):
            p["reps"] = max(p.get("reps", 3) - 1, 2); p["pct"] = round(p.get("pct", DEFAULT_PCT[key]) * 0.97, 3)
        elif key == "vo2_3015":
            p["sets"] = max(p.get("sets", 3) - 1, 2)
        elif key == "over_under":
            p["reps"] = max(p.get("reps", 3) - 1, 2)
        elif key == "endurance":
            p["minutes"] = round(p.get("minutes", 60) * 0.75)
        elif key == "ftp_test":
            key, p = "endurance", {"minutes": 45, "pct": 0.65}
            day["note"] = "Test postponed (amber). Retest on the next green day."
        day["status"] = "amber-adjusted"
    else:  # red
        if key in KEY_SESSIONS:
            # move the key session to a later easy day whose neighbours are not key sessions
            days = plan["days"]
            is_key = lambda i: 0 <= i < len(days) and days[i]["session"] in KEY_SESSIONS and days[i]["date"] != date
            ok = [d for i, d in enumerate(days)
                  if d["date"] > date and weekday(d["date"]) not in REST_REQUIRED
                  and d["session"] in ("endurance", "recovery", "rest") and not d.get("moved_from")
                  and not is_key(i - 1) and not is_key(i + 1)]
            # prefer normal training days; an optional rest day (Sat) is the last resort
            ok.sort(key=lambda d: (weekday(d["date"]) in REST_OPTIONAL, d["date"]))
            target = ok[0] if ok else None
            if target is None and orig["session"] == "ftp_test":
                # the test outranks a training session: take the next key slot (never a required rest day)
                target = next((d for d in days if d["date"] > date and d["session"] in KEY_SESSIONS
                               and weekday(d["date"]) not in REST_REQUIRED), None)
            if target is not None:
                target.update(session=orig["session"], params=orig["params"], moved_from=date, status="moved",
                              note=f"Moved from {date} (red readiness).")
            else:
                day["note"] = "Key session dropped this week (no safe slot). Weekly review will rebuild."
        key, p = "recovery", {"minutes": 30}
        day["status"] = "red-swapped"
        day["note"] = ("Recovery day: " + "; ".join(r["flags"]) + ". " + day.get("note", "")).strip()
    day["original"] = orig
    day["session"], day["params"] = key, p
    save_plan(plan_path, plan)
    build(plan_path)
    return r


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"build": lambda: build(*args), "show": lambda: show(*args),
     "readiness": lambda: print(json.dumps(readiness(*args), indent=1)),
     "pivot": lambda: pivot(*args)}[cmd]()
