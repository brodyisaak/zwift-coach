# apple health → training/health (10-minute setup)

the coach reads `health/daily.csv`. `tools/health_parse.py` builds it from whatever lands in `health/raw/` (health auto export json/csv) or `health/apple_health_export/export.xml` (full apple export). metrics used: **hrv (sdnn), resting hr, sleep, respiratory rate**. vo2 max is optional.

## step 1 — backfill a baseline today (free, one-time)

readiness needs 7+ days of history before it can flag anything. a full export gives it months on day one.

1. iphone → **health** → your profile photo → **export all health data** → export
2. airdrop `export.zip` to this mac
3. unzip it into this folder so the file sits at `training/health/apple_health_export/export.xml`

## step 2 — daily automatic export (health auto export, premium)

1. install **health auto export – json+csv** (iphone). automatic exports need premium (7-day free trial; monthly, annual or lifetime)
2. **automations → new automation → icloud drive**
   - data type: **health metrics**
   - metrics: **heart rate variability, resting heart rate, sleep analysis, respiratory rate** (optional: vo2 max)
   - format: **json** · aggregation: **day** · summarize sleep: **on**
   - date range: **previous 7 days** (overlap is fine, newest wins)
   - schedule: daily at **5:45 am**, before the morning coach routine runs
   - folder name: `training-health`
3. open the app once each morning for the first few days. ios only runs background exports reliably once it has learned the habit

## step 3 — point the coach at the export folder

health auto export writes into icloud drive (finder → icloud drive → health auto export → `training-health`). then either:
- **option a (recommended):** give the assistant access to that `training-health` folder and set `health_source_dir` in `config.json` to its path
- **option b:** each morning the scheduled check copies new files into `health/raw/` itself, once `health_source_dir` is set

## wear the watch to bed

hrv and resting hr come from overnight apple watch readings. without sleep data the readiness check runs on hr/hrv alone and says so.

## what the coach does with it

see `coach.md` → readiness rules. short version: green = ride as written; amber = trim (one fewer rep, −3% watts, shorter z2); red = 30 min recovery spin and the key session moves to a safe later slot. this is not medical advice: if the data and how you feel both point to illness, rest.

## live setup — apple shortcuts (free)

**shortcut "training health export"** (iphone) appends one header-less line per morning to icloud drive → shortcuts → `training-health.csv`:
`yyyy-MM-dd, HRV ms, resting HR, sleep_today_s, resp rate, sleep_since_yesterday_s`

1. find health samples: heart rate variability, start date **is today** (overnight readings) → calculate statistics: average
2. find health samples: resting heart rate, last 1 day → average
3. find health samples: sleep, start date **is today**, value does not contain "awake" / "bed" → get details: duration → sum (seconds)
4. find health samples: respiratory rate, start date **is today**, **limit 10** → average
5. format date: current date, custom `yyyy-MM-dd` → text `date,HRV,RHR,sleep_today,RR` → append to `training-health.csv` (new line on)
6. find health samples: sleep, start date in the last 1 day, same value filters → duration → sum → append `,<sum>` (new line off)

**automations (all run training health export automatically, no notification):**
- when waking up. usually runs before the watch has synced last night's sleep: gives hrv and resting hr.
- daily at 7:25 am. fails silently if the phone is locked (ios blocks health data on a locked phone).
- **when strava is opened**. the reliable one: the phone is unlocked and you're up, so the sleep data is there.

several lines per day are expected. `health_parse.py` keeps the most complete run per day (largest since-yesterday sleep value). sleep for night d needs a complete line on day d-1 as well.

why two sleep sums: shortcuts' "in the last 1 day" is a calendar window (yesterday 00:00 → now), so it catches two nights. `health_parse.py` computes last night = since_yesterday(today) − today(yesterday). needs one previous morning's line, so sleep appears from the second morning. values outside 1–11 h are dropped.

permissions granted: shortcuts reads hrv, resting hr, sleep and respiratory rate only (past 30 days + future); the two append steps are set to always allow. rr is capped at 10 samples to stay under the ios limit on health items written to a file (151 was blocked; 88 + 35 pass). if the limit is ever hit again: settings → apps → shortcuts → advanced → allow sharing large amounts of data.

mac side: `config.json` → `health_source_dir` points at `~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents` (connected folder). icloud often keeps the file cloud-only, so the morning routine should download it first. in finder you can right-click the file → keep downloaded to make this unnecessary.
