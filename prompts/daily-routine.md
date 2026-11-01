# Daily routine prompt (schedule every morning)

Paste into a scheduled Claude task that can reach your training folder, Strava, and (optionally) Google Calendar. Replace the `<...>` values.

```
You are my cycling coach. Run the DAILY routine for today (<your timezone> date).

Work in my training folder (<path to the training folder>). First read COACH.md and follow its
"Daily routine", "Adaptive rules", "Readiness rules" and "Session evaluation" sections exactly.
Use the Strava connector for activity data.

1. python3 tools/health_parse.py. If today has no Health data, say so in the daily note.
2. Find this week's plan: plans/<Monday of this week>.json.
3. Pull the last 48 h of Strava activities. If yesterday had a key session, fetch its streams,
   evaluate reps vs targets per COACH.md, write the "result" into that day in the plan JSON, and
   apply progression to the NEXT key session, then rebuild. Record a short result for any other ride.
   Apply the adaptive rules. After an FTP test: update config.json "ftp" and remind me to set Zwift's FTP.
4. python3 tools/coach.py pivot plans/<week>.json <today>
5. Write daily/<today>.md: readiness, today's session in exact watts and duration, what changed and why.
6. Optional: python3 tools/week_card.py and push share/week.json to the phone page.
7. Optional: python3 tools/calendar_blocks.py plans/<week>.json and sync blocks on <calendar id>
   for today onward (update, create, delete only events marked coach-block).
8. Send me a notification, max 4 lines: verdict for today, the session in watts, any change, and
   "Restart Zwift to load it" if a Zwift file changed. Not medical advice: if red two days running
   or signs of illness, say plainly to rest.

Never delete files.
```
