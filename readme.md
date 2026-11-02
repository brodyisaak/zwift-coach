# zwift-coach

a small, file-based cycling coach that plans your season, writes structured workouts straight into zwift, and adjusts them every day from your recovery data and your last ride.

built for one rider chasing **289 → 330 w ftp over a winter on zwift**. shared as a template you can adapt.

<img src="docs/phone-page.png" alt="weekly plan on a phone: week snapshot, gate progress, readiness and a card per workout with its power profile" width="320">

## what it does

- **plans the season.** blocks of 3 build weeks + 1 recovery week, with ftp test gates along the way. pyramidal intensity in the base phase, polarized before the peak. the reasoning and sources are in [`research/`](research/aerobic-anaerobic-balance.md)
- **writes the workouts.** every session is generated in exact watts and saved as a zwift custom workout (`.zwo`), one fixed slot per weekday, so zwift's list never fills up
- **adjusts daily.** each morning it reads apple health readiness (hrv, resting hr, sleep, breathing rate) and yesterday's strava ride. hit every rep with heart rate to spare: the next session progresses. poor recovery: today gets trimmed or swapped for a recovery spin, and the key session moves to a safe day
- **reviews weekly.** hours, training load, intensity split against target, key sessions hit, best efforts, gate status, then it builds next week
- **keeps easy days interesting.** z2 rides rotate through cadence ladders, seated hills, 10-s sprinkles and power pyramids instead of flat steady riding
- **shows up where you look.** an optional phone page with the week as an activity feed, and optional calendar blocks around your work schedule

## how it runs

the engine is plain python. the coaching judgement comes from an ai assistant (built and run with [claude](https://claude.ai)) that follows a written rulebook, [`COACH.md`](COACH.md), on a schedule:

| when | routine | prompt |
|---|---|---|
| every morning | read readiness and yesterday's ride, score key sessions, progress or trim, rewrite today's zwift file | [`prompts/daily-routine.md`](prompts/daily-routine.md) |
| sunday evening | weekly review and next week's plan | [`prompts/weekly-review.md`](prompts/weekly-review.md) |

the assistant needs access to this folder, your strava account and, if you use the calendar blocks, google calendar. you can also run every tool by hand without any ai.

## quick start

requirements: python 3.9+, `numpy` (for ride metrics only), zwift with a smart trainer.

```bash
git clone https://github.com/brodyisaak/zwift-coach.git && cd zwift-coach
cp config.example.json config.json            # set your ftp, gates, zwift id and folder
cp plans/example-week.json plans/2026-11-02.json   # name plans by their monday
python3 tools/coach.py show  plans/2026-11-02.json  # check the week in watts
python3 tools/coach.py build plans/2026-11-02.json  # write the .zwo files into zwift
```

restart zwift, then open **workouts → custom workouts**. your zwift id is the folder name under `~/Documents/Zwift/Workouts/`.

**zwift's ftp must match `config.json`.** workouts are stored as % of ftp, so a mismatch shifts every target.

## tools

```bash
python3 tools/coach.py build plans/<week>.json        # write the week's .zwo files into zwift
python3 tools/coach.py show  plans/<week>.json        # print the week in watts
python3 tools/coach.py readiness [YYYY-MM-DD]         # green / amber / red from health/daily.csv
python3 tools/coach.py pivot plans/<week>.json [DATE] # apply readiness to a day and rebuild
python3 tools/health_parse.py                         # apple health exports -> health/daily.csv
python3 tools/ride_metrics.py streams.json <FTP>      # np, tss, zone minutes, best 1/5/20/60 min
python3 tools/week_card.py [--next]                   # data for the phone page -> share/week.json
python3 tools/calendar_blocks.py plans/<week>.json    # calendar blocks for a week (json)
```

### session library

| key | session | main params |
|---|---|---|
| `ftp_test` | 5-min benchmark + 20-min test | — |
| `threshold` | sub-threshold / threshold reps | `reps`, `on_sec`, `pct`, `off_sec` |
| `vo2_3015` | 30/15 short intervals | `sets`, `reps`, `pct` |
| `vo2_long` | 4–5 min vo2 reps | `reps`, `on_sec`, `pct` |
| `over_under` | over-unders | `reps`, `blocks`, `under`, `over` |
| `sweet_spot` | sweet spot reps | `reps`, `on_sec`, `pct` |
| `endurance` | z2 in four formats | `minutes`, `pct`, `style` (`ladder` / `hills` / `sprinkles` / `pyramid`), `finish_sprints`, `late_efforts`, `fuel_every_min` |
| `recovery` · `openers` · `rest` | — | — |

`pct` is a fraction of ftp. a plan is one mon–sun json file; see [`plans/example-week.json`](plans/example-week.json). generated examples are in [`examples/zwo/`](examples/zwo/).

## readiness rules (summary)

baseline is your previous 28 days. full rules in [`COACH.md`](COACH.md).

| status | triggers | what changes |
|---|---|---|
| green | no flags | ride as written |
| amber | hrv z < −1, resting hr > +3 bpm, or sleep 5.5–6.5 h | key session −1 rep and −3%, z2 −25%, tests postponed |
| red | hrv z < −2, resting hr > +5 two days running, sleep < 5.5 h, breathing rate > +1.5, or two amber flags | 30-min recovery spin; key session moves to a safe day or drops |

apple health setup (free, with an iphone shortcut) is in [`health/README.md`](health/README.md).

## folder layout

| path | what |
|---|---|
| `COACH.md` | the rulebook the routines follow |
| `season-plan.md` | example 27-week plan: blocks, gates, intensity balance, weekly template |
| `research/` | evidence summary behind the intensity balance |
| `config.example.json` | copy to `config.json` and fill in |
| `plans/` | one json file per week |
| `tools/` | the engine |
| `prompts/` | templates for the daily and weekly routines |
| `web/training-week.html` | phone page (renders `share/week.json`) |
| `examples/zwo/` | sample generated zwift workouts |

your own data (`config.json`, health data, dated plans, daily notes, reviews, training log) is in `.gitignore` so it stays local.

## notes

- not medical advice. if your data and how you feel both point to illness or overreaching, rest
- the training rules are a starting point built for one rider. adjust `COACH.md` and `season-plan.md` to your goals, hours and history

## licence

mit
