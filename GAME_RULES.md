# GAME_RULES.md — World Cup 2026 Prediction Game

> **This file is the single source of truth for all game logic.**
> Edit values here, not in code. When this file changes, the app's scoring,
> phases, badges, and forms must be updated to match. All numbers below are
> **PLACEHOLDERS** — change freely.

---

## Overview

A private World Cup 2026 prediction game for a group of friends. Players make
predictions across three phases; points are awarded as real results come in;
a live leaderboard tracks standings. No money, no betting. Social hype happens
on WhatsApp; the website only handles gameplay.

---

## Phases

There are three phases. Each player makes **one submission per phase**, editable
until that phase locks.

### Phase 1 — Group Stage Predictions
- **Opens:** before the first World Cup match.
- **Locks:** automatically when the first match kicks off.
- **Players predict:**
  - Group winners and runners-up (per group)
  - Total tournament goals
  - Top scorer (Golden Boot)
  - Best player (Golden Ball)
  - Surprise team / dark horse
  - One free-text wildcard prediction (admin scores manually)

### Phase 2 — Knockout Predictions
- **Opens:** immediately after the group stage ends.
- **Locks:** before the first knockout match starts.
- **Players predict:**
  - Full knockout bracket
  - Round of 32 winners
  - Quarterfinalists
  - Semifinalists
  - Finalists
  - Champion
  - Final scoreline
  - Penalty shootout count (how many knockout ties go to penalties)
  - Golden Boot winner

### Phase 3 — Chaos Round
- **Opens:** near the semifinals/final (admin triggers manually).
- **Locks:** short window, admin-set deadline.
- **Only 3–5 quick predictions**, e.g.:
  - Will the final go to penalties?
  - Who scores first in the final?
  - Which semifinal has more goals?
  - Exact final score
  - Total red cards remaining in tournament
- **Rule:** adds drama, must NOT outweigh Phases 1–2.

---

## Scoring (PLACEHOLDER VALUES — edit freely)

| Prediction | Points |
|---|---|
| Correct group winner | +2 |
| Correct group runner-up | +2 |
| Total tournament goals (exact / within range) | +10 / +5 |
| Top scorer (Golden Boot) | +10 |
| Best player (Golden Ball) | +10 |
| Surprise team / dark horse | +8 |
| Wildcard | variable bonus, admin-assigned |
| Round of 32 winner (each) | +3 |
| Quarterfinalist (each) | +5 |
| Semifinalist (each) | +8 |
| Finalist (each) | +10 |
| Champion | +20 |
| Exact final score | +25 |
| Penalty shootout count correct | +8 |
| Chaos Round item (each) | +5 |

### Optional scoring (off by default — enable if wanted)
- **Knockout streak bonus:** +X for N consecutive correct knockout picks.
- **Perfect-group bonus:** flat bonus if a player gets an entire group right.

> Keep scoring simple. Do not invent additional conditions beyond this table.

---

## Badges

Displayed beside usernames. Auto-awarded where possible; admin can assign manually.

| Badge | Earned by |
|---|---|
| **Oracle** | Perfect group-stage prediction |
| **Clutch** | Correct champion pick |
| **Chaos Agent** | Successful wildcard prediction |
| **Underdog Prophet** | Correctly predicted a surprise semifinalist |

---

## Core gameplay rules

- **Hidden predictions:** players CANNOT see each other's picks until a phase
  locks. This is mandatory — without it, people copy.
- **One submission per phase**, editable until lock, frozen after.
- **Leaderboard goes live** once Phase 1 locks, then updates whenever the admin
  enters results and triggers recalculation.
- **Scoring is recalculated**, never incrementally patched — recompute every
  player's total from stored predictions + stored results so edits stay correct.

---

## Admin capabilities

- Create player accounts; reset passwords manually.
- Open / close each phase.
- Enter real match results.
- Trigger score recalculation.
- Assign badges manually.
- Trigger / open the Chaos Round.

No automation beyond this. No live data feeds — admin enters results by hand.

---

## Player-facing screens (logic, not design)

- **Login:** username + password only. No email, no verification.
- **Dashboard:** current phase, deadlines, submission status, leaderboard
  snapshot, earned badges, recent updates.
- **Prediction forms:** mobile-first, one per phase, editable before deadline.
- **Leaderboard:** total points, rank, rank movement, highlight current player,
  badge icons, recent gains.
