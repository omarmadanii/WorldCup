# GAME_RULES.md — World Cup 2026 Prediction Game

> **This file is the single source of truth for all game logic.**
> When this file changes, the app's scoring, phases, and forms must be updated to match.

---

## Overview

A private World Cup 2026 prediction game for a small group of friends. Players make
predictions across three phases; points are awarded as real results come in;
a live leaderboard tracks standings. No money, no betting.

Points **accumulate** across all three phases — your total is the sum of Phases 1, 2, and 3.

---

## Phases

Each player makes **one submission per phase**, editable until that phase locks,
frozen after. No player can see another player's picks until the phase closes.

### Phase 1 — Group Stage Predictions
- **Opens:** before the first World Cup match.
- **Locks:** when the first match kicks off.
- **Players predict:**
  - Group qualifiers: pick the top-2 finishers from each of the 12 groups (A–L)
  - Total tournament goals
  - Tournament champion — early pick before the tournament starts
  - Top scorer / Golden Boot — 3 ranked choices
  - Best player / Golden Ball — 3 ranked choices
  - الرابحة — one free-text prediction of a surprising event (admin scores manually)
  - اختبار الدهاء — 5 fun questions, 1 pt each

### Phase 2 — Knockout Bracket
- **Opens:** after the group stage ends and the admin enters the 16 R32 fixtures.
- **Locks:** before the first knockout match starts.
- **Players predict via an interactive bracket:**
  - Pick the winner of each Round of 32 match (16 matches)
  - Winners cascade into Round of 16, Quarterfinals, Semifinals, and Final
  - Dark horse — a team that reaches the Quarterfinals despite low expectations
  - Exact final score

### Phase 3 — Chaos Round
- **Opens:** after the semi-finals end (admin triggers manually).
- **Locks:** short window, admin-set deadline.
- **5 questions about the final match:**
  1. Will the final go to a penalty shootout? (yes/no)
  2. Who scores the first goal in the final? (open text)
  3. How many goals will be scored in the final? (number)
  4. Will there be a red card in the final? (yes/no)
  5. Who wins the Man of the Match award in the final? (open text)

---

## Scoring

### Phase 1 — Group Stage

| Prediction | Points |
|---|---|
| Predicted team qualifies from their group (either position) | +1 |
| Position also correct (1st or 2nd) | +1 bonus |
| **Max per group** | **4 pts** (2 picks × up to 2 pts each) |
| Total tournament goals — exact | +10 |
| Total tournament goals — within ±5 | +5 |
| Tournament champion (early Phase 1 pick) | +15 |
| Golden Boot — 1st choice correct | +10 |
| Golden Boot — 2nd choice correct | +7 |
| Golden Boot — 3rd choice correct | +5 |
| Golden Ball — 1st choice correct | +10 |
| Golden Ball — 2nd choice correct | +7 |
| Golden Ball — 3rd choice correct | +5 |
| الرابحة (free text event) | variable, admin-assigned |
| اختبار الدهاء (5 questions) | +1 each (max 5) |

> For Golden Boot / Golden Ball, only the **first matching choice** awards points — no stacking.

### Phase 2 — Knockout Bracket

| Prediction | Points |
|---|---|
| Correct R32 winner (each of 16 matches) | +3 |
| Correct Quarterfinalist (each of 8) | +5 |
| Correct Semifinalist (each of 4) | +8 |
| Correct Finalist (each of 2) | +10 |
| Correct Champion | +20 |
| Dark horse (reaches QF — admin confirms) | +8 |
| Exact final score | +10 |

### Phase 3 — Chaos Round

| Prediction | Points |
|---|---|
| Each correct answer (5 questions) | +2 |
| **Max Phase 3 total** | **10 pts** |

> Phase 3 is intentionally small — it adds drama without overturning the Phase 1–2 standings.

---

## Core gameplay rules

- **Hidden predictions:** players cannot see each other's picks until a phase locks.
- **Points accumulate** across all three phases — there is no per-phase reset.
- **Leaderboard goes live** once Phase 1 locks, then updates whenever the admin
  enters results and triggers recalculation.
- **Scoring is always recalculated fresh** from stored predictions + stored results.
  Points are never patched in-place.
- **Bracket is fully fixed** from the Round of 32 onwards — no re-draws between rounds.
  The admin enters the 16 R32 fixtures once; the bracket path is determined automatically.

---

## Admin responsibilities

- Create player accounts; reset passwords.
- Enter the **16 R32 fixtures** (team pairings) before opening Phase 2.
- Open and close each phase manually.
- Enter real match results for each round.
- Trigger score recalculation after entering results.
- Assign الرابحة points (any amount) and اختبار الدهاء points (0–5) per player.
- Confirm the dark horse result for Phase 2 scoring.

No live data feeds — admin enters all results by hand.

---

## Player-facing screens

- **Login:** username + password only.
- **Dashboard:** current phase status, countdown, submission progress, leaderboard snapshot.
- **Phase 1 form:** group picks (A–L), total goals, champion, golden boot/ball (3 choices each), الرابحة, اختبار الدهاء.
- **Phase 2 form:** interactive bracket → R32 → R16 → QF → SF → Final; dark horse; exact final score.
- **Phase 3 form:** 5 final-match questions.
- **Leaderboard:** total points, rank, current-player highlight.
- **Rules page:** scoring breakdown for all three phases (in-app).
