# Weekly review prompt (schedule Sunday evening)

Paste into a scheduled Claude task that can reach your training folder, Strava, and (optionally) Google Calendar. Replace the `<...>` values.

```
You are my cycling coach. Run the WEEKLY REVIEW and build NEXT WEEK's Zwift plan.

Work in my training folder (<path to the training folder>). First read COACH.md, season-plan.md,
research/aerobic-anaerobic-balance.md, config.json, the last two weekly reviews, this week's plan
(with results) and the last 4 rows of training-log.md. Follow COACH.md "Weekly routine" and
"Methods and definitions" exactly. Use the Strava connector for activity data.

1. python3 tools/health_parse.py, then summarise readiness for the week.
2. Pull the last 7 days from Strava. For non-commute rides fetch streams and run tools/ride_metrics.py
   with the FTP in config.json. Compare with the previous 4 weeks. Report the intensity split against
   the season-plan target. Run the 3-week trend check.
3. Write weekly-reviews/<today>.md: verdict and gate status; key numbers; what worked / what didn't
   (max 3 each); next week's plan in exact watts.
4. Build next week (keep plans/<next Monday>.json if it already exists, adjusting only key-session
   params). Session keys come from tools/coach.py LIB. Then python3 tools/coach.py build on it.
5. Append a row to training-log.md.
6. Optional: python3 tools/week_card.py --next and push it to the phone page; sync next week's
   calendar blocks with tools/calendar_blocks.py.
7. Send me a notification, max 8 lines: verdict, gate status, next week's 7 days in one line each,
   and "Restart Zwift to load the new workouts". Not medical advice.

Never delete files.
```
