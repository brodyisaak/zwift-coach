# Apple Health → training/health (10-minute setup)

The coach reads `health/daily.csv`. `tools/health_parse.py` builds it from whatever lands in `health/raw/` (Health Auto Export JSON/CSV) or `health/apple_health_export/export.xml` (full Apple export). Metrics used: **HRV (SDNN), resting HR, sleep, respiratory rate**. VO2 max is optional.

## Step 1 — Backfill a baseline today (free, one-time)

Readiness needs 7+ days of history before it can flag anything. A full export gives it months on day one.

1. iPhone → **Health** → your profile photo → **Export All Health Data** → Export
2. AirDrop `export.zip` to this Mac
3. Unzip it into this folder so the file sits at `training/health/apple_health_export/export.xml`

## Step 2 — Daily automatic export (Health Auto Export, Premium)

1. Install **Health Auto Export – JSON+CSV** (iPhone). Automatic exports need Premium (7-day free trial; monthly, annual or lifetime)
2. **Automations → New Automation → iCloud Drive**
   - Data type: **Health Metrics**
   - Metrics: **Heart Rate Variability, Resting Heart Rate, Sleep Analysis, Respiratory Rate** (optional: VO2 Max)
   - Format: **JSON** · Aggregation: **Day** · Summarize sleep: **On**
   - Date range: **Previous 7 days** (overlap is fine, newest wins)
   - Schedule: daily at **5:45 am**, before the morning coach routine runs
   - Folder name: `training-health`
3. Open the app once each morning for the first few days. iOS only runs background exports reliably once it has learned the habit

## Step 3 — Point the coach at the export folder

Health Auto Export writes into iCloud Drive (Finder → iCloud Drive → Health Auto Export → `training-health`). Then either:
- **Option A (recommended):** give the assistant access to that `training-health` folder and set `health_source_dir` in `config.json` to its path
- **Option B:** each morning the scheduled check copies new files into `health/raw/` itself, once `health_source_dir` is set

## Wear the watch to bed

HRV and resting HR come from overnight Apple Watch readings. Without sleep data the readiness check runs on HR/HRV alone and says so.

## What the coach does with it

See `COACH.md` → Daily pivot rules. Short version: green = ride as written; amber = trim (one fewer rep, −3% watts, shorter Z2); red = 30 min recovery spin and the key session moves to a safe later slot. This is not medical advice: if the data and how you feel both point to illness, rest.

## Live setup — Apple Shortcuts (free)

**Shortcut "Training Health Export"** (iPhone) appends one header-less line per morning to iCloud Drive → Shortcuts → `training-health.csv`:
`yyyy-MM-dd, HRV ms, resting HR, sleep_today_s, resp rate, sleep_since_yesterday_s`

1. Find Health Samples: Heart Rate Variability, start date **is today** (overnight readings) → Calculate Statistics: Average
2. Find Health Samples: Resting Heart Rate, last 1 day → Average
3. Find Health Samples: Sleep, start date **is today**, value does not contain "Awake" / "Bed" → Get Details: Duration → Sum (seconds)
4. Find Health Samples: Respiratory Rate, start date **is today**, **limit 10** → Average
5. Format Date: Current Date, custom `yyyy-MM-dd` → Text `date,HRV,RHR,sleep_today,RR` → Append to `training-health.csv` (new line on)
6. Find Health Samples: Sleep, start date in the last 1 day, same value filters → Duration → Sum → Append `,<sum>` (new line off)

**Automations (all run Training Health Export automatically, no notification):**
- When Waking Up. Usually runs before the Watch has synced last night's sleep: gives HRV and resting HR.
- Daily at 7:25 am. Fails silently if the phone is locked (iOS blocks Health data on a locked phone).
- **When Strava is opened**. The reliable one: the phone is unlocked and you're up, so the sleep data is there.

Several lines per day are expected. `health_parse.py` keeps the most complete run per day (largest since-yesterday sleep value). Sleep for night D needs a complete line on day D-1 as well.

Why two sleep sums: Shortcuts' "in the last 1 day" is a calendar window (yesterday 00:00 → now), so it catches two nights. `health_parse.py` computes last night = since_yesterday(today) − today(yesterday). Needs one previous morning's line, so sleep appears from the second morning. Values outside 1–11 h are dropped.

Permissions granted: Shortcuts reads HRV, Resting HR, Sleep and Respiratory Rate only (past 30 days + future); the two Append steps are set to Always Allow. RR is capped at 10 samples to stay under the iOS limit on Health items written to a file (151 was blocked; 88 + 35 pass). If the limit is ever hit again: Settings → Apps → Shortcuts → Advanced → Allow Sharing Large Amounts of Data.

Mac side: `config.json` → `health_source_dir` points at `~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents` (connected folder). iCloud often keeps the file cloud-only, so the morning routine should download it first. In Finder you can right-click the file → Keep Downloaded to make this unnecessary.
