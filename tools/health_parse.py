#!/usr/bin/env python3
"""Build health/daily.csv from Apple Health data. Standard library only.

Sources (all optional, merged, newest wins):
  1. Health Auto Export JSON files: health/raw/*.json (and the folder in config.json "health_source_dir")
  2. Health Auto Export CSV files:  health/raw/*.csv
  3. Apple Health full export:      health/export.xml or health/apple_health_export/export.xml (backfill)

Output columns: date, hrv (ms, SDNN, overnight/morning mean), rhr (bpm), sleep_h (asleep hours,
attributed to the wake-up date), resp_rate (breaths/min), vo2max.

Usage: python3 tools/health_parse.py [--days 120]
"""
import csv, datetime as dt, glob, json, os, re, shutil, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, "health")
RAW = os.path.join(H, "raw")
_cfg = os.path.join(ROOT, "config.json")
CFG = json.load(open(_cfg if os.path.exists(_cfg) else os.path.join(ROOT, "config.example.json")))

# metric name variants -> our key
NAMES = {
    "heart_rate_variability": "hrv", "heart_rate_variability_sdnn": "hrv", "hrv": "hrv",
    "heartratevariabilitysdnn": "hrv", "resting_heart_rate": "rhr", "restingheartrate": "rhr",
    "respiratory_rate": "resp_rate", "respiratoryrate": "resp_rate",
    "vo2_max": "vo2max", "vo2max": "vo2max", "sleep_analysis": "sleep", "sleepanalysis": "sleep",
}
HK = {"HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv", "HKQuantityTypeIdentifierRestingHeartRate": "rhr",
      "HKQuantityTypeIdentifierRespiratoryRate": "resp_rate", "HKQuantityTypeIdentifierVO2Max": "vo2max"}
ASLEEP = {"HKCategoryValueSleepAnalysisAsleep", "HKCategoryValueSleepAnalysisAsleepCore",
          "HKCategoryValueSleepAnalysisAsleepDeep", "HKCategoryValueSleepAnalysisAsleepREM",
          "HKCategoryValueSleepAnalysisAsleepUnspecified"}

def parse_ts(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            t = dt.datetime.strptime(s, fmt)
            return t.replace(tzinfo=None)  # keep local wall-clock time
        except ValueError:
            pass
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return dt.datetime.fromisoformat(m.group(1)) if m else None

samples = defaultdict(lambda: defaultdict(list))   # key -> date -> [(datetime, value)]
sleep = defaultdict(float)                          # wake date -> hours asleep

def add(key, t, v):
    if t is None or v in (None, ""):
        return
    try:
        v = float(v)
    except (TypeError, ValueError):
        return
    samples[key][t.date().isoformat()].append((t, v))

def from_hae_json(path):
    try:
        d = json.load(open(path))
    except Exception as e:
        print("skip", path, e); return
    metrics = d.get("data", d).get("metrics", []) if isinstance(d, dict) else []
    for m in metrics:
        key = NAMES.get(re.sub(r"[^a-z0-9_]", "", m.get("name", "").lower()))
        if not key:
            continue
        for row in m.get("data", []):
            if key == "sleep":
                end = parse_ts(row.get("sleepEnd") or row.get("endDate") or row.get("date"))
                hrs = row.get("asleep") or row.get("totalSleep")
                if hrs is None and any(k in row for k in ("core", "deep", "rem")):
                    hrs = sum(float(row.get(k) or 0) for k in ("core", "deep", "rem"))
                if end and hrs:
                    hrs = float(hrs)
                    if (m.get("units") or "hr").startswith("min"):
                        hrs /= 60
                    sleep[end.date().isoformat()] = max(sleep[end.date().isoformat()], hrs)
            else:
                add(key, parse_ts(row.get("date")), row.get("qty", row.get("Avg", row.get("avg"))))

def from_hae_csv(path):
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            t = parse_ts(row.get("Date/Time") or row.get("Date") or row.get("date") or "")
            for col, v in row.items():
                c = (col or "").lower()
                if "variability" in c: add("hrv", t, v)
                elif "resting heart rate" in c: add("rhr", t, v)
                elif "respiratory rate" in c: add("resp_rate", t, v)
                elif "vo2" in c: add("vo2max", t, v)
                elif c.startswith("sleep analysis [asleep]") or c.startswith("sleep analysis [total]"):
                    if t and v:
                        sleep[t.date().isoformat()] = max(sleep[t.date().isoformat()], float(v))

def seed_from_daily():
    """Fallback when export.xml is unreadable: reuse the history already in daily.csv."""
    path = os.path.join(H, "daily.csv")
    if not os.path.exists(path):
        return
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            t = dt.datetime.fromisoformat(row["date"] + "T06:00:00")
            for k in ("hrv", "rhr", "resp_rate", "vo2max"):
                add(k, t, row.get(k))
            if row.get("sleep_h"):
                sleep[row["date"]] = float(row["sleep_h"])

def from_export_xml(path, since):
    import xml.etree.ElementTree as ET
    intervals = defaultdict(list)
    for _, el in ET.iterparse(path, events=("end",)):
        if el.tag != "Record":
            el.clear(); continue
        typ = el.get("type")
        start = parse_ts(el.get("startDate"))
        if start and start.date() >= since:
            if typ in HK:
                add(HK[typ], start, el.get("value"))
            elif typ == "HKCategoryTypeIdentifierSleepAnalysis" and el.get("value") in ASLEEP:
                end = parse_ts(el.get("endDate"))
                if end:
                    intervals[end.date().isoformat()].append((start, end))
        el.clear()
    for day, iv in intervals.items():  # merge overlapping intervals from multiple sources
        iv.sort(); tot, cur_s, cur_e = 0, None, None
        for s, e in iv:
            if cur_e is None or s > cur_e:
                if cur_e: tot += (cur_e - cur_s).total_seconds()
                cur_s, cur_e = s, e
            else:
                cur_e = max(cur_e, e)
        if cur_e: tot += (cur_e - cur_s).total_seconds()
        sleep[day] = max(sleep[day], tot / 3600)

def from_shortcut_csv(path):
    """Free Apple Shortcuts export: header-less lines, one or more per day:
        yyyy-MM-dd, hrv_ms, rhr_bpm, sleep_today_s, resp_rate, sleep_since_yday_s
    Shortcuts' "in the last 1 day" is a calendar window (yesterday 00:00 -> now), so it covers two nights.
    Night D = since_yday(D) - today(D-1). Several runs a day are expected: per day we keep the most complete
    run (largest since_yday, i.e. the latest one after the Watch synced), and the last non-blank HRV/RHR/RR.
    Results outside 1-11 h are treated as missing (Watch had not synced yet)."""
    def num(x):
        try: return float(x)
        except (ValueError, TypeError): return None
    days = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if len(row) < 3 or not re.match(r"\d{4}-\d{2}-\d{2}$", row[0].strip()):
                continue
            c = [x.strip() for x in row[1:6]] + [""] * (5 - len(row[1:6]))
            d = days.setdefault(row[0].strip(), {"hrv": None, "rhr": None, "rr": None, "today": None, "since": None})
            for k, v in (("hrv", c[0]), ("rhr", c[1]), ("rr", c[3])):
                if num(v) is not None: d[k] = num(v)
            if len(row) < 6 and num(c[2]) is not None:   # legacy 5-column test rows (Oct 18): sleep field meant something else
                continue
            for k, v in (("today", c[2]), ("since", c[4])):
                if num(v) is not None and (d[k] is None or num(v) > d[k]): d[k] = num(v)
    for d, v in days.items():
        t = dt.datetime.fromisoformat(d + "T07:00:00")
        for key, k in (("hrv", "hrv"), ("rhr", "rhr"), ("resp_rate", "rr")):
            if v[k] is not None: add(key, t, v[k])
        prev = days.get((dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat())
        if v["since"] is not None and prev and prev["today"] is not None:
            hrs = (v["since"] - prev["today"]) / 3600
            if 1 <= hrs <= 11:
                sleep[d] = hrs

def is_shortcut_csv(path):
    with open(path, newline="") as f:
        first = f.readline()
    return bool(re.match(r"\d{4}-\d{2}-\d{2},", first))

def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 180
    since = dt.date.today() - dt.timedelta(days=days)
    os.makedirs(RAW, exist_ok=True)
    src = os.path.expanduser(CFG.get("health_source_dir") or "")
    if src and not os.path.isdir(src):  # remote shells may mount connected folders at ~/mnt/<folder name>
        alt = os.path.expanduser(os.path.join("~/mnt", os.path.basename(src.rstrip("/"))))
        src = alt if os.path.isdir(alt) else src
    if src and os.path.isdir(src):  # copy new exports from the iCloud folder into health/raw
        for p in glob.glob(os.path.join(src, "**", "*.json"), recursive=True) + glob.glob(os.path.join(src, "**", "*.csv"), recursive=True):
            dst = os.path.join(RAW, os.path.basename(p))
            if not os.path.exists(dst) or os.path.getmtime(p) > os.path.getmtime(dst):
                try:
                    shutil.copy2(p, dst)
                except OSError as e:  # iCloud file not downloaded yet ("Resource deadlock avoided")
                    print(f"skip {p}: {e} (stage the file to download it, then rerun)")
    for xmlp in [os.path.join(H, "export.xml"), os.path.join(H, "apple_health_export", "export.xml")]:
        if os.path.exists(xmlp):
            print("parsing", xmlp)
            try:
                from_export_xml(xmlp, since)
            except OSError as e:  # iCloud evicted the backfill ("Resource deadlock avoided")
                print(f"skip {xmlp}: {e}; seeding history from existing daily.csv instead")
                samples.clear(); sleep.clear(); seed_from_daily()
    for p in sorted(glob.glob(os.path.join(RAW, "*.json"))):
        from_hae_json(p)
    for p in sorted(glob.glob(os.path.join(RAW, "*.csv"))):
        from_shortcut_csv(p) if is_shortcut_csv(p) else from_hae_csv(p)
    dates = sorted(set(d for k in samples for d in samples[k]) | set(sleep))
    out = os.path.join(H, "daily.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "hrv", "rhr", "sleep_h", "resp_rate", "vo2max"])
        for d in dates:
            if d < since.isoformat():
                continue
            def val(k):
                xs = samples[k].get(d, [])
                if not xs: return ""
                if k == "hrv":  # prefer overnight/morning readings (00:00-09:00)
                    am = [v for t, v in xs if t.hour < 9]
                    xs_v = am or [v for _, v in xs]
                    return round(sum(xs_v) / len(xs_v), 1)
                if k == "rhr":
                    return round(min(v for _, v in xs), 1)
                return round(sum(v for _, v in xs) / len(xs), 1)
            w.writerow([d, val("hrv"), val("rhr"), round(sleep[d], 2) if d in sleep else "", val("resp_rate"), val("vo2max")])
    print(f"wrote {out}: {len(dates)} days")

if __name__ == "__main__":
    main()
