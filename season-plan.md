# Example season plan — 289 → 330 W FTP in 27 weeks

A worked example. Copy it, change the dates, FTP and gates to yours, and keep `config.json` `gates` in sync with the table below.

27 weeks, seven blocks. Blocks of 3 build weeks + 1 recovery week, except the final peak block. Every watt target is rescaled from the latest tested FTP.

## Targets and gates (Zwift 20-min tests)

| Date | Gate | If missed |
|---|---|---|
| Wed Oct 21 | Baseline test: **289 W** (best 20 min 304 W) | Done |
| **Sun Dec 13** | **≥ 300 W** | < 295 → spring goal becomes 315 |
| **Sun Feb 7** | **≥ 315 W** | < 308 → spring goal becomes 320 |
| **Sun Apr 25** | **330 W** | — |

## Blocks

Built from `research/aerobic-anaerobic-balance.md`. **30/15s are now the main VO2 session**, and sub-threshold work starts in Block 1. FTP 289 W (tested Oct 21).

| # | Dates | Focus | Key 1 (Tue) | Key 2 (Thu) | Long ride (Sun) | Hours/wk |
|---|---|---|---|---|---|---|
| 1 | Oct 19 – Nov 15 | Rebuild + test | Sub-threshold 4×8 → 4×10 → 3×12 @ 88–92% | 30/15s 3×10 → 3×12 @ 120–122% | 2–2.5 h Z2, finish sprints every 2nd week | 7.5–8 |
| 2 | Nov 16 – Dec 13 | Threshold foundation | 3×12 → 3×15 → 2×20 @ 92–95% | 30/15s 3×13 @ 122–125% | 2–2.5 h; from Dec: 2×10 @ 88–90% in the last 40 min | 8–9 |
| 3 | Dec 14 – Jan 10 | Holiday volume | Over-unders 3×(4×3 min) | 30/15s, or 5×4 min @ 113% every 2nd week for variety | 2.5–3 h with late efforts, 2–3 long rides | 9–10 |
| 4 | Jan 11 – Feb 7 | Threshold extension | 2×20 → 3×15 → 2×25 @ 95–100% | 30/15s 3×13 @ 125% | 2.5–3 h, late efforts 2×12 @ 90% | 9–10 |
| 5 | Feb 8 – Mar 7 | Shift to polarized (3 quality) | 2×20 @ 100% | 5×5 @ 112% and 30/15s (alternate weeks) | Long ride with 2×20 @ 90% late (Q3) | 10 |
| 6 | Mar 8 – Apr 4 | Race-specific / outdoor transition | 2×30 @ 95%, or 60 min @ 90% | 6×4 @ 115% | Outdoor long rides | 9–10 |
| 7 | Apr 5 – Apr 25 | Peak + taper | Openers, 2×10 @ 100% | Short VO2 | Volume −40%; test Sun Apr 25 | 9 → 6 |

## Intensity balance (by time, all rides)

| Phase | Low (<75% FTP) | Moderate (75–105%) | High (>105%) |
|---|---|---|---|
| Blocks 1–4 (to Feb 7): pyramidal | ~78% | ~16% | ~6% |
| Blocks 5–7 (Feb 8 on): polarized | ~80% | ~10% | ~10% |

- **Anaerobic dose:** every second week, 5 × 20 s sprints at the end of the Sunday ride (`finish_sprints`). Also sprinkles inside one Z2 ride a week. Never the day before a key session. For a rider whose top end is already strong (5-min power well above 120% of FTP), the limiter is threshold, so anaerobic work is maintenance and variety, never a block focus.
- **Durability:** from December the long ride ends with quality on tired legs (`late_efforts`). Fuel 90–120 g carbs/h on rides over 2 h.
- **Strength:** heavy legs (4–8 RM: squat or leg press, RDL, split squat; 2–3 sets) 2× a week Nov–Feb, ideally after Tue/Thu rides so easy days stay easy. 1× a week from March. Stop 10 days before the Apr 25 test.
- **Watts:** 30/15s at 120–125% = 347–361 W. Sub-threshold at 88–92% = 254–266 W. Threshold at 95–100% = 275–289 W.

Recovery weeks: Nov 9–15, Dec 7–13, Jan 4–10, Feb 1–7, Mar 1–7, Mar 29–Apr 4. Each one is about 60% volume, keeps openers and ends with a test or benchmark.

## Weekly template

| Day | Default | Notes |
|---|---|---|
| Mon | Z2 45–60 min @ 185–205 W | Easy after the long ride. Commute counts as extra |
| Tue | **Q1** (VO2 or threshold) | Zwift, ERG |
| Wed | Z2 60 min @ 185–205 W | Commute counts as extra |
| Thu | **Q2** | Zwift, ERG |
| Fri | **Rest (fixed)** | Never trained, never used for a moved session |
| Sat | Optional rest, or Z2 60–90 min | Your call on the day. Key sessions land here only if no other slot exists |
| Sun | **Long ride** 2–3 h Z2 (outdoor when dry) | Tempo inserts from Block 4; **Q3** as threshold inserts from Block 5. Optional race replaces Q2/Q3, never added |

## Non-negotiables

- Two structured key sessions every week, even in busy weeks. Cut the Z2 rides before the key sessions
- Nothing between 210 and 250 W unless it's prescribed
- One race per week maximum, and it counts as a key session
- Daily readiness check (Apple Health) decides whether today runs as written, gets trimmed, or swaps. See `COACH.md`
- Missing a key session doesn't mean doubling up. The plan moves it or drops it
