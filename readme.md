# zwift-coach

plans a cycling season, writes each workout into zwift in exact watts, and adjusts today's session each morning based on recovery data from apple health and yesterday's ride on strava

built for my own winter block, 289 to 330 w ftp by april 25 on 7.5–10 hours a week. fork it and change the numbers in `config.json` and `season-plan.md` to use it for yours

<img src="docs/phone-page.png" alt="the weekly plan on a phone: week snapshot, gate progress, readiness and a card for each workout" width="320">

## how it works

1. the iphone exports last night's hrv, resting hr, sleep and respiratory rate to icloud
2. `health_parse.py` turns the export into `health/daily.csv`
3. `coach.py pivot` scores readiness as green, amber or red against the last 28 days
4. today's session is kept, trimmed or swapped, and the zwift file is rewritten
5. strava data from yesterday's key session sets the targets for the next one

claude runs steps 2–5 every morning and builds the next week every sunday. every step can also be run by hand

<img src="docs/morning-run.png" alt="terminal: health_parse.py writes daily.csv, then pivot flags amber for short sleep and trims thursday's 30/15s from 3 sets to 2" width="720">

sample run. sleep was 6.1 h, which is amber, so thursday's 30/15s went from 3 sets to 2

## apple health setup

a free shortcut called **training health export** reads hrv, resting hr, sleep and respiratory rate and appends one line to `iCloud Drive/Shortcuts/training-health.csv`

<p>
<img src="docs/shortcut-hrv-rhr.webp" alt="the shortcut in the shortcuts editor: find health samples for heart rate variability starting today, average them, then find resting heart rate over the last 1 day" width="260">
<img src="docs/shortcut-sleep-append.webp" alt="the shortcut's last steps: build the text line from the date and averages, append it to training-health.csv with make new line on, then find sleep samples over the last 1 day, excluding awake and bed" width="260">
</p>

each metric is a find health samples step followed by an average, or a sum for sleep. a text step joins them into one line and append writes it to the csv with make new line on

three automations run the shortcut

| trigger | notes |
|---|---|
| when waking up | gets hrv and resting hr. sleep usually hasn't synced yet |
| daily at 7:25 am | backup. fails if the phone is locked because ios blocks health data on a locked phone |
| when strava is opened | most reliable. phone is unlocked and sleep has synced |

<img src="docs/automation-strava.webp" alt="the automation: when strava is opened, run training health export" width="320">

that gives a few lines per day. `health_parse.py` keeps the most complete one for each day

<img src="docs/health-pipeline.png" alt="terminal: raw shortcut lines with two runs per day, then the parsed daily.csv with hrv, resting hr, sleep hours and respiratory rate" width="720">

### setup notes

- "last 1 day" in shortcuts runs from midnight yesterday, so it covers two nights. the shortcut logs two sleep totals and the parser subtracts one from the other. sleep data starts on the second morning
- ios blocks a shortcut from writing too many health samples to a file. respiratory rate is limited to 10 samples for this reason
- icloud can leave the csv cloud-only on the mac. right-click it in finder and choose keep downloaded
- set both append steps to always allow or the automation will wait for a tap
- the watch has to be worn overnight for hrv and resting hr

for history on day one, export all health data from the health app and unzip it into `health/apple_health_export/`. full shortcut steps and a paid option (health auto export) are in [`health/readme.md`](health/readme.md)

## readiness rules

<img src="docs/amber-day.png" alt="phone card for thursday: key session, amber adjusted, 30/15s 2x12 at 352 w, 50 minutes" width="400">

baseline is the previous 28 days. hrv uses a 3-day rolling average

| status | triggers | change |
|---|---|---|
| green | no flags | ride as written |
| amber | hrv z < −1, resting hr > +3 bpm, or sleep 5.5–6.5 h | key session loses one rep and 3% watts, z2 cut by 25%, ftp tests postponed |
| red | hrv z < −2, resting hr > +5 two days running, sleep < 5.5 h, respiratory rate > +1.5, or two amber flags | 30-min recovery spin. key session moves to a later safe day or drops |

a safe day isn't a required rest day and isn't next to another key session. running the pivot more than once on the same day won't trim the session twice

## progression

after each key session the routine pulls the strava streams and checks each rep. a rep counts if average power is within 3% of target for 95% of it

- all reps done with hr to spare: +5 w or +1 rep next time
- one rep missed: repeat the session
- two or more missed: −5 w and check readiness and fuelling
- long rides: hr drift under 5% adds 15 min next time. over 8% keeps the duration and adds a fuelling cue every 15 min

full rules are in [`coach.md`](coach.md). change coaching behaviour there, not in the prompts

## zwift workouts

each weekday has a fixed file, `COACH_1_Mon.zwo` to `COACH_7_Sun.zwo`, overwritten every week so the custom workouts list stays the same length. power is stored as a percentage of ftp, so zwift's ftp setting has to match `config.json`

<img src="docs/long-ride.png" alt="phone card for sunday: cadence ladder, 150 minutes at about 202 w, with a flat z2 power profile" width="400">

z2 rides rotate through four formats

- ladder: similar power with cadence at 85, 95, 105 and 115 rpm every 10 min
- hills: 4 min seated at 70 rpm near the top of z2, then 3 min at 95 rpm
- sprinkles: a 10-s acceleration every 8 min. not used the day before a key session or on rides of 90 min or more
- pyramid: 3-min steps from 62% to 74% of ftp and back with changing cadence

long rides can add late efforts or finishing sprints and get a fuelling cue every 20 min

## setup

requires python 3.9+, `numpy` for ride metrics, and zwift with a smart trainer

```bash
git clone https://github.com/brodyisaak/zwift-coach.git && cd zwift-coach
cp config.example.json config.json                  # ftp, gates, zwift id, health folder
cp plans/example-week.json plans/2026-11-02.json    # plans are named by their monday
python3 tools/coach.py show  plans/2026-11-02.json  # check the week in watts
python3 tools/coach.py build plans/2026-11-02.json  # write the .zwo files into zwift
```

restart zwift and go to workouts > custom workouts. your zwift id is the folder name under `~/Documents/Zwift/Workouts/`

to automate it, add [`prompts/daily-routine.md`](prompts/daily-routine.md) as a scheduled claude task every morning and [`prompts/weekly-review.md`](prompts/weekly-review.md) every sunday evening. claude needs access to this folder and strava. google calendar is optional and used for ride blocks

<details>
<summary><b>commands</b></summary>

```bash
python3 tools/health_parse.py                         # apple health to health/daily.csv
python3 tools/coach.py readiness [YYYY-MM-DD]         # green, amber or red
python3 tools/coach.py pivot plans/<week>.json [DATE] # apply readiness and rebuild
python3 tools/coach.py build plans/<week>.json        # write the week into zwift
python3 tools/coach.py show  plans/<week>.json        # print the week in watts
python3 tools/ride_metrics.py streams.json <FTP>      # np, tss, zones, best 1/5/20/60 min
python3 tools/week_card.py [--next]                   # phone page data to share/week.json
python3 tools/calendar_blocks.py plans/<week>.json    # calendar blocks for the week
```

</details>

<details>
<summary><b>session library</b></summary>

| key | session | params |
|---|---|---|
| `ftp_test` | 5-min benchmark + 20-min test | none |
| `threshold` | sub-threshold and threshold reps | `reps`, `on_sec`, `pct`, `off_sec` |
| `vo2_3015` | 30/15s | `sets`, `reps`, `pct` |
| `vo2_long` | 4–5 min vo2 reps | `reps`, `on_sec`, `pct` |
| `over_under` | over-unders | `reps`, `blocks`, `under`, `over` |
| `sweet_spot` | sweet spot reps | `reps`, `on_sec`, `pct` |
| `endurance` | z2 in four styles | `minutes`, `pct`, `style`, `late_efforts`, `finish_sprints`, `fuel_every_min` |
| `recovery`, `openers`, `rest` | | none |

`pct` is a fraction of ftp. each plan is one json file for monday to sunday. see [`plans/example-week.json`](plans/example-week.json) and [`examples/zwo/`](examples/zwo/)

</details>

<details>
<summary><b>folder layout</b></summary>

| path | contents |
|---|---|
| `coach.md` | rules the routines follow |
| `season-plan.md` | blocks, gates and weekly template |
| `research/` | evidence for the intensity balance |
| `health/` | apple health setup and local health data |
| `plans/` | one json file per week |
| `tools/` | python scripts |
| `prompts/` | daily and weekly routine prompts |
| `web/training-week.html` | phone page |
| `docs/` | screenshots. terminal and phone page images use sample data |
| `examples/zwo/` | sample zwift workouts |

</details>

## season plan

27 weeks in seven blocks, mostly three build weeks and one recovery week, with ftp tests on dec 13, feb 7 and apr 25. pyramidal intensity in the base phase and polarized from feb 8. details in [`season-plan.md`](season-plan.md) and [`research/`](research/aerobic-anaerobic-balance.md)

## notes

- `config.json`, health exports, dated plans, daily notes, reviews and the training log are in `.gitignore` and stay local
- not medical advice. if the data and how you feel both point to illness or overreaching, rest
- the rules are set for one rider's history and hours. adjust `coach.md` and `season-plan.md` to suit

## licence

mit
