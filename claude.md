# CLAUDE.md — World Cup 2026 Prediction Game

## What this is

A private, one-time World Cup 2026 prediction game for a small group of friends.
It is deliberately small. Build the simplest thing that works. Resist every urge
to add infrastructure this project does not need.

**Game logic lives in `GAME_RULES.md`.** That file is the source of truth for
phases, scoring, and forms. When it changes, update the code to match.
Do not hardcode game values that contradict it; read them from there
(or from a config derived from it) so edits stay in one place.

---

## Stack (defaults — deviate only with a stated reason)

- **Backend:** Flask
- **DB:** SQLite (single file)
- **Templates:** Jinja2
- **Styling:** plain HTML + Tailwind (via CDN is fine for this scale)
- **Auth:** Flask sessions, username + password, hashed (werkzeug). No email,
  no reset flow, no third-party auth.

These are sensible defaults, not dogma. If something genuinely calls for a
different choice, say so and explain why before reaching for it — but the bar
is high. The whole point is to avoid a build pipeline for what is a handful
of forms and a leaderboard.

### Do NOT add
- React or any frontend build step
- WebSockets / real-time anything
- Push notifications
- Docker / Kubernetes / microservices
- Public registration
- External match-data APIs (admin enters results by hand)
- A scoring engine with hundreds of conditions
- Badge icons, badge screens, or any achievements system — the design has none

---

## Design System

The visual design is established in `World Cup 2026 Mockup.html` (archived in the
design bundle). All templates must match it. Key specs follow.

### Language & layout

- Every page: `<html dir="rtl" lang="ar">`
- Google Fonts CDN: `Tajawal` (wght 400–900) + `Bebas Neue`
- Phone-only: single column, `max-w-[420px]` centred. No desktop breakpoints.
- All UI text in Arabic. Western numerals (1, 2, 3) are fine in leaderboards.

### Colour palette

Copy this verbatim into every template's `tailwind.config` script block:

```js
tailwind.config = {
  theme: {
    extend: {
      colors: {
        pitch: { 950:'#062a17', 900:'#073a1f', 800:'#0a4d29', 700:'#0a6b3a',
                 600:'#118a4c', 500:'#1aa55e', 400:'#3cc77c', 300:'#86e3ad' },
        warm:  { 700:'#a8311d', 600:'#c93b22', 500:'#e2452a',
                 400:'#ef6a4f', 300:'#f59578' },
        sand:  { 50:'#fdfaf3', 100:'#fbf6ec', 200:'#f3ead7', 300:'#e7d8b3' },
        ink:   { 900:'#0e1413', 700:'#2b3433', 500:'#5a6664', 400:'#7c8786' },
      },
      fontFamily: {
        sans:    ['Tajawal', 'system-ui', 'sans-serif'],
        display: ['"Bebas Neue"', 'Tajawal', 'sans-serif'],
      },
    }
  }
}
```

### Global CSS (goes in `base.html` `<style>` block)

```css
html, body { background: #0e1413; font-family: 'Tajawal', system-ui, sans-serif; }

/* Faint vertical pitch stripes — used as section-header accents */
.pitch-stripes {
  background-image:
    repeating-linear-gradient(90deg, rgba(255,255,255,0.04) 0 28px,
    rgba(255,255,255,0) 28px 56px);
}

/* Stadium spotlight behind hero headers */
.stadium-glow {
  background:
    radial-gradient(120% 60% at 50% -10%, rgba(60,199,124,0.25), transparent 60%),
    radial-gradient(80% 40% at 100% 0%, rgba(226,69,42,0.18), transparent 60%);
}

/* Tabular numerals for scores/points */
.tabular { font-variant-numeric: tabular-nums; }

/* Hide scrollbar on horizontal scroll strips */
.scroll-x { scrollbar-width: none; }
.scroll-x::-webkit-scrollbar { display: none; }

/* Pulsing ring on the current-user leaderboard row */
@keyframes meRing {
  0%, 100% { box-shadow: 0 0 0 0 rgba(226,69,42,0.55); }
  50%       { box-shadow: 0 0 0 6px rgba(226,69,42,0); }
}
.me-row { animation: meRing 2.4s ease-out infinite; }
```

### Component patterns

| Component | Tailwind / markup pattern |
|---|---|
| **Hero header** | `bg-pitch-900 stadium-glow overflow-hidden` + `pitch-stripes` strip pinned to bottom |
| **White card** | `bg-white rounded-2xl ring-1 ring-black/5 shadow-sm` |
| **Primary button** | `bg-warm-500 hover:bg-warm-600 text-white font-extrabold rounded-2xl h-14` |
| **Countdown digits** | `font-display text-[44px] leading-none tabular` inside dark card |
| **Progress ring** | SVG `<circle>` pair; inner `stroke-dasharray/offset` drives fill percentage |
| **Leaderboard dark card** | `bg-pitch-950 text-sand-50 rounded-3xl ring-1 ring-black/30` |
| **Rank number** | `font-display text-2xl tabular leading-none`; rank 1 in `text-warm-400` |
| **Rank movement arrow** | Inline SVG triangle (up = `pitch-400`, down = `warm-600`, flat = `ink-400` dash) |
| **Current-user row** | `bg-warm-500/15 border-y-2 border-warm-500 me-row`; avatar gets `ring-2 ring-warm-300/60` |
| **"أنت" pill** | `text-[9px] bg-warm-500 text-white px-1.5 py-px rounded font-bold` |
| **Podium (top 3)** | 3-col grid, centre col tallest bar; rank 1 avatar: `ring-4 ring-warm-300/40` |
| **Prediction select** | `bg-sand-100 rounded-xl h-12 px-3 font-bold appearance-none` + custom SVG chevron in `background-image` style |
| **Group card** | `bg-white rounded-2xl ring-1 ring-black/5`; incomplete groups get `ring-warm-500/40` |
| **Wildcard textarea** | Dark card `bg-pitch-900`; `<textarea>` uses `bg-ink-900/40 ring-1 ring-white/10 rounded-xl` |
| **Sticky submit bar** | `fixed bottom-16 inset-x-0 px-5 z-30 max-w-[420px] mx-auto` (sits above bottom nav) |
| **Recent-gains strip** | Horizontal `scroll-x overflow-x-auto` row of `rounded-full` pills |

### Bottom navigation

Three tabs: **الرئيسية · التوقعات · الترتيب**

- Hidden on the login screen: `{% if current_user.is_authenticated %}` wrapper in `base.html`
- Active tab: `text-pitch-700`; inactive: `text-ink-400`
- `h-16` fixed bar with `bg-white/95 backdrop-blur border-t border-black/5`

### Jinja porting notes

- **Strip the screen-picker pill** from the mockup — it is a dev helper, not a
  real UI element.
- Current-user row highlight → use `{% if player.id == current_user.id %}` to
  add `me-row bg-warm-500/15 border-y-2 border-warm-500` classes.
- `meRing` animation lives in `base.html`; import it once.
- Navigation active state → pass `active_tab` from each route, compare in the
  nav template macro.
- Countdown timer → rendered as a static string server-side or via a small
  vanilla JS `setInterval`; no library needed.

---

## Project structure (greenfield — create this)

```
worldcup-predictions/
├── app.py                # Flask app, routes
├── models.py             # SQLite schema / data access
├── scoring.py            # reads GAME_RULES values, computes standings
├── config.py             # secrets, paths, env-driven settings
├── GAME_RULES.md         # canonical game spec (edit this for rule changes)
├── CLAUDE.md             # this file
├── requirements.txt
├── database.db           # SQLite (gitignored)
├── static/
│   └── css/              # Tailwind output or custom CSS
└── templates/
    ├── base.html         # shared layout, nav, theme
    ├── login.html
    ├── dashboard.html
    ├── predict_phase1.html
    ├── predict_phase2.html
    ├── predict_phase3.html
    ├── leaderboard.html
    └── admin/
        ├── results.html
        └── players.html
```

Adjust if a cleaner layout emerges, but keep it flat. No premature packages.

---

## Conventions

- **Recalculate, don't increment.** Standings are always computed fresh from
  stored predictions + stored results. Never patch a running total in place.
- **Hidden predictions are enforced server-side.** A player must never be able
  to fetch another player's picks before a phase locks — not via template, not
  via route. Treat this as a security boundary, not a UI nicety.
- **Lock state is checked on the server** before accepting any submission edit.
- Keep routes thin; put game logic in `scoring.py` / `models.py`.
- Mobile-first: most users open this from a WhatsApp link on a phone.
- Plain, readable code over clever abstractions. A future-me with no context
  should understand any file in two minutes.

---

## Deployment

Target is a cheap VPS (provider TBD). Keep deployment boring:
- Run under a production WSGI server (gunicorn) behind nginx.
- SQLite file on local disk; back it up by copying the file.
- Secrets (Flask secret key, admin credentials) from environment variables
  via `config.py` — never committed.

Don't build deployment automation yet. A short README with the manual steps
is enough until it's actually running.

---

## When in doubt

Ask before adding a dependency, a table, or a phase of complexity. The failure
mode for this project is over-engineering, not under-engineering.
