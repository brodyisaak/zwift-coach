# example season plan — 289 → 330 w ftp in 27 weeks

a worked example. copy it, change the dates, ftp and gates to yours, and keep `config.json` `gates` in sync with the table below.

27 weeks, seven blocks. blocks of 3 build weeks + 1 recovery week, except the final peak block. every watt target is rescaled from the latest tested ftp.

## targets and gates (zwift 20-min tests)

| date | gate | if missed |
|---|---|---|
| wed oct 21 | baseline test: **289 w** (best 20 min 304 w) | done |
| **sun dec 13** | **≥ 300 w** | < 295 → spring goal becomes 315 |
| **sun feb 7** | **≥ 315 w** | < 308 → spring goal becomes 320 |
| **sun apr 25** | **330 w** | — |

## blocks

built from `research/aerobic-anaerobic-balance.md`. **30/15s are now the main vo2 session**, and sub-threshold work starts in block 1. ftp 289 w (tested oct 21).

| # | dates | focus | key 1 (tue) | key 2 (thu) | long ride (sun) | hours/wk |
|---|---|---|---|---|---|---|
| 1 | oct 19 – nov 15 | rebuild + test | sub-threshold 4×8 → 4×10 → 3×12 @ 88–92% | 30/15s 3×10 → 3×12 @ 120–122% | 2–2.5 h z2, finish sprints every 2nd week | 7.5–8 |
| 2 | nov 16 – dec 13 | threshold foundation | 3×12 → 3×15 → 2×20 @ 92–95% | 30/15s 3×13 @ 122–125% | 2–2.5 h; from dec: 2×10 @ 88–90% in the last 40 min | 8–9 |
| 3 | dec 14 – jan 10 | holiday volume | over-unders 3×(4×3 min) | 30/15s, or 5×4 min @ 113% every 2nd week for variety | 2.5–3 h with late efforts, 2–3 long rides | 9–10 |
| 4 | jan 11 – feb 7 | threshold extension | 2×20 → 3×15 → 2×25 @ 95–100% | 30/15s 3×13 @ 125% | 2.5–3 h, late efforts 2×12 @ 90% | 9–10 |
| 5 | feb 8 – mar 7 | shift to polarized (3 quality) | 2×20 @ 100% | 5×5 @ 112% and 30/15s (alternate weeks) | long ride with 2×20 @ 90% late (q3) | 10 |
| 6 | mar 8 – apr 4 | race-specific / outdoor transition | 2×30 @ 95%, or 60 min @ 90% | 6×4 @ 115% | outdoor long rides | 9–10 |
| 7 | apr 5 – apr 25 | peak + taper | openers, 2×10 @ 100% | short vo2 | volume −40%; test sun apr 25 | 9 → 6 |

## intensity balance (by time, all rides)

| phase | low (<75% ftp) | moderate (75–105%) | high (>105%) |
|---|---|---|---|
| blocks 1–4 (to feb 7): pyramidal | ~78% | ~16% | ~6% |
| blocks 5–7 (feb 8 on): polarized | ~80% | ~10% | ~10% |

- **anaerobic dose:** every second week, 5 × 20 s sprints at the end of the sunday ride (`finish_sprints`). also sprinkles inside one z2 ride a week. never the day before a key session. for a rider whose top end is already strong (5-min power well above 120% of ftp), the limiter is threshold, so anaerobic work is maintenance and variety, never a block focus.
- **durability:** from december the long ride ends with quality on tired legs (`late_efforts`). fuel 90–120 g carbs/h on rides over 2 h.
- **strength:** heavy legs (4–8 rm: squat or leg press, rdl, split squat; 2–3 sets) 2× a week nov–feb, ideally after tue/thu rides so easy days stay easy. 1× a week from march. stop 10 days before the apr 25 test.
- **watts:** 30/15s at 120–125% = 347–361 w. sub-threshold at 88–92% = 254–266 w. threshold at 95–100% = 275–289 w.

recovery weeks: nov 9–15, dec 7–13, jan 4–10, feb 1–7, mar 1–7, mar 29–apr 4. each one is about 60% volume, keeps openers and ends with a test or benchmark.

## weekly template

| day | default | notes |
|---|---|---|
| mon | z2 45–60 min @ 185–205 w | easy after the long ride. commute counts as extra |
| tue | **q1** (vo2 or threshold) | zwift, erg |
| wed | z2 60 min @ 185–205 w | commute counts as extra |
| thu | **q2** | zwift, erg |
| fri | **rest (fixed)** | never trained, never used for a moved session |
| sat | optional rest, or z2 60–90 min | your call on the day. key sessions land here only if no other slot exists |
| sun | **long ride** 2–3 h z2 (outdoor when dry) | tempo inserts from block 4; **q3** as threshold inserts from block 5. optional race replaces q2/q3, never added |

## non-negotiables

- two structured key sessions every week, even in busy weeks. cut the z2 rides before the key sessions
- nothing between 210 and 250 w unless it's prescribed
- one race per week maximum, and it counts as a key session
- daily readiness check (apple health) decides whether today runs as written, gets trimmed, or swaps. see `coach.md`
- missing a key session doesn't mean doubling up. the plan moves it or drops it
