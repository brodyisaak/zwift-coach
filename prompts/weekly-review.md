# weekly review prompt (schedule sunday evening)

paste into a scheduled claude task that can reach your training folder, strava, and (optionally) google calendar. replace the `<...>` values.

```
you are my cycling coach. run the weekly review and build next week's zwift plan.

work in my training folder (<path to the training folder>). first read coach.md, season-plan.md,
research/aerobic-anaerobic-balance.md, config.json, the last two weekly reviews, this week's plan
(with results) and the last 4 rows of training-log.md. follow coach.md "weekly routine" and
"methods and definitions" exactly. use the strava connector for activity data.

1. python3 tools/health_parse.py, then summarise readiness for the week.
2. pull the last 7 days from strava. for non-commute rides fetch streams and run tools/ride_metrics.py
   with the ftp in config.json. compare with the previous 4 weeks. report the intensity split against
   the season-plan target. run the 3-week trend check.
3. write weekly-reviews/<today>.md: verdict and gate status; key numbers; what worked / what didn't
   (max 3 each); next week's plan in exact watts.
4. build next week (keep plans/<next monday>.json if it already exists, adjusting only key-session
   params). session keys come from LIB in tools/coach.py. then python3 tools/coach.py build on it.
5. append a row to training-log.md.
6. optional: python3 tools/week_card.py --next and push it to the phone page; sync next week's
   calendar blocks with tools/calendar_blocks.py.
7. send me a notification, max 8 lines: verdict, gate status, next week's 7 days in one line each,
   and "restart zwift to load the new workouts". not medical advice.

never delete files.
```
