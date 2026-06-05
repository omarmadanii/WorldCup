"""
models.py — SQLite schema and all data-access functions.
No business logic here; pure CRUD + schema.
"""
import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import DATABASE, ADMIN_USERNAME, ADMIN_PASSWORD


# ── Connection ─────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    UNIQUE NOT NULL,
    password_hash TEXT   NOT NULL,
    is_admin     INTEGER DEFAULT 0,
    prev_rank    INTEGER DEFAULT 0,
    created_at   TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS phases (
    id       INTEGER PRIMARY KEY,
    name     TEXT    NOT NULL,
    status   TEXT    DEFAULT 'pending',   -- pending | open | locked
    deadline TEXT                          -- ISO 8601 datetime or NULL
);

-- Phase 1: Group-stage predictions
-- group_picks: JSON {"A":{"winner":"...","runner":"..."}, ...}
CREATE TABLE IF NOT EXISTS phase1_predictions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER UNIQUE NOT NULL REFERENCES users(id),
    group_picks  TEXT    DEFAULT '{}',
    total_goals  INTEGER,
    golden_boot  TEXT,
    golden_ball  TEXT,
    dark_horse   TEXT,
    wildcard     TEXT,
    wildcard_pts INTEGER DEFAULT 0,    -- admin-assigned wildcard bonus
    champion_p1       TEXT,
    golden_boot_2     TEXT,
    golden_boot_3     TEXT,
    golden_ball_2     TEXT,
    golden_ball_3     TEXT,
    dawha_ronaldo     TEXT,
    dawha_bulga_goals INTEGER,
    dawha_uncle       TEXT,
    dawha_jeddah      TEXT,
    dawha_car         TEXT,
    dawha_pts         INTEGER DEFAULT 0,
    submitted_at TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

-- Phase 2: Knockout predictions
-- r32_winners / quarterfinalists / semifinalists / finalists: JSON arrays
CREATE TABLE IF NOT EXISTS phase2_predictions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER UNIQUE NOT NULL REFERENCES users(id),
    r32_winners      TEXT    DEFAULT '[]',
    quarterfinalists TEXT    DEFAULT '[]',
    semifinalists    TEXT    DEFAULT '[]',
    finalists        TEXT    DEFAULT '[]',
    champion         TEXT,
    final_home_goals INTEGER,
    final_away_goals INTEGER,
    penalties_count  INTEGER,
    golden_boot      TEXT,
    dark_horse       TEXT,
    submitted_at     TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);

-- Phase 3: Chaos-round predictions
CREATE TABLE IF NOT EXISTS phase3_predictions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER UNIQUE NOT NULL REFERENCES users(id),
    final_to_penalties   INTEGER,   -- 1=yes 0=no
    first_scorer         TEXT,
    more_goals_semi      TEXT,
    exact_final_home     INTEGER,
    exact_final_away     INTEGER,
    red_cards_remaining  INTEGER,
    final_goals          INTEGER,   -- total goals in the final
    red_card_final       INTEGER,   -- 1=yes 0=no
    mom_final            TEXT,      -- man of the match
    submitted_at         TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

-- Results entered by admin (key → JSON-encoded value)
CREATE TABLE IF NOT EXISTS results (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Activity feed for dashboard "recent updates"
CREATE TABLE IF NOT EXISTS activity (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message    TEXT NOT NULL,
    detail     TEXT,
    category   TEXT DEFAULT 'info',  -- info | result | rank
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db():
    """Create tables and seed the admin account + 3 phases."""
    with get_db() as db:
        db.executescript(SCHEMA)

        # Seed phases 1–3 if not present
        for phase_id, name in [(1, 'دور المجموعات'),
                                (2, 'دور الخروج'),
                                (3, 'جولة الفوضى')]:
            db.execute(
                'INSERT OR IGNORE INTO phases (id, name, status) VALUES (?, ?, ?)',
                (phase_id, name, 'pending')
            )

        # Migrate phase2_predictions
        for col_def in ['dark_horse TEXT']:
            try:
                db.execute(f'ALTER TABLE phase2_predictions ADD COLUMN {col_def}')
                db.commit()
            except Exception:
                pass

        # Migrate phase3_predictions
        for col_def in ['final_goals INTEGER', 'red_card_final INTEGER', 'mom_final TEXT']:
            try:
                db.execute(f'ALTER TABLE phase3_predictions ADD COLUMN {col_def}')
                db.commit()
            except Exception:
                pass

        # Migrate existing DBs: add new columns if missing
        for col_def in [
            'champion_p1 TEXT',
            'golden_boot_2 TEXT',
            'golden_boot_3 TEXT',
            'golden_ball_2 TEXT',
            'golden_ball_3 TEXT',
            'dawha_ronaldo TEXT',
            'dawha_bulga_goals INTEGER',
            'dawha_uncle TEXT',
            'dawha_jeddah TEXT',
            'dawha_car TEXT',
            'dawha_pts INTEGER DEFAULT 0',
        ]:
            try:
                db.execute(f'ALTER TABLE phase1_predictions ADD COLUMN {col_def}')
                db.commit()
            except Exception:
                pass  # column already exists

        # Seed admin user if not present
        existing = db.execute(
            'SELECT id FROM users WHERE username = ?', (ADMIN_USERNAME,)
        ).fetchone()
        if not existing:
            db.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)',
                (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD))
            )
        db.commit()


# ── Users ──────────────────────────────────────────────────────────────────

def get_user_by_id(user_id):
    with get_db() as db:
        return db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()


def get_user_by_username(username):
    with get_db() as db:
        return db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()


def list_users(include_admin=True):
    with get_db() as db:
        if include_admin:
            return db.execute('SELECT * FROM users ORDER BY username').fetchall()
        return db.execute(
            'SELECT * FROM users WHERE is_admin = 0 ORDER BY username'
        ).fetchall()


def create_user(username, password, is_admin=0):
    with get_db() as db:
        db.execute(
            'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), is_admin)
        )
        db.commit()


def set_password(user_id, new_password):
    with get_db() as db:
        db.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(new_password), user_id)
        )
        db.commit()


def verify_password(username, password):
    """Return the user row if credentials are valid, else None."""
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


def snapshot_ranks(ranks_by_user_id):
    """Persist current ranks into prev_rank before a new calculation."""
    with get_db() as db:
        for user_id, rank in ranks_by_user_id.items():
            db.execute(
                'UPDATE users SET prev_rank = ? WHERE id = ?', (rank, user_id)
            )
        db.commit()


# ── Phases ─────────────────────────────────────────────────────────────────

def get_phase(phase_num):
    with get_db() as db:
        return db.execute('SELECT * FROM phases WHERE id = ?', (phase_num,)).fetchone()


def get_all_phases():
    with get_db() as db:
        return db.execute('SELECT * FROM phases ORDER BY id').fetchall()


def set_phase_status(phase_num, status):
    with get_db() as db:
        db.execute('UPDATE phases SET status = ? WHERE id = ?', (status, phase_num))
        db.commit()


def set_phase_deadline(phase_num, deadline_str):
    """deadline_str: ISO 8601 string or empty string to clear."""
    value = deadline_str.strip() or None
    with get_db() as db:
        db.execute('UPDATE phases SET deadline = ? WHERE id = ?', (value, phase_num))
        db.commit()


# ── Phase 1 predictions ────────────────────────────────────────────────────

def get_phase1_prediction(user_id):
    with get_db() as db:
        row = db.execute(
            'SELECT * FROM phase1_predictions WHERE user_id = ?', (user_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d['group_picks'] = json.loads(d['group_picks'] or '{}')
    return d


def save_phase1_prediction(user_id, data: dict):
    group_picks_json = json.dumps(data.get('group_picks', {}), ensure_ascii=False)
    now = datetime.utcnow().isoformat(timespec='seconds')
    with get_db() as db:
        existing = db.execute(
            'SELECT id FROM phase1_predictions WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            db.execute("""
                UPDATE phase1_predictions
                SET group_picks=?, total_goals=?, golden_boot=?,
                    golden_boot_2=?, golden_boot_3=?,
                    golden_ball=?, golden_ball_2=?, golden_ball_3=?,
                    dark_horse=?, wildcard=?, champion_p1=?,
                    dawha_ronaldo=?, dawha_bulga_goals=?, dawha_uncle=?,
                    dawha_jeddah=?, dawha_car=?, updated_at=?
                WHERE user_id=?
            """, (group_picks_json,
                  data.get('total_goals'),
                  data.get('golden_boot') or None,
                  data.get('golden_boot_2') or None,
                  data.get('golden_boot_3') or None,
                  data.get('golden_ball') or None,
                  data.get('golden_ball_2') or None,
                  data.get('golden_ball_3') or None,
                  data.get('dark_horse') or None,
                  data.get('wildcard') or None,
                  data.get('champion_p1') or None,
                  data.get('dawha_ronaldo') or None,
                  data.get('dawha_bulga_goals'),
                  data.get('dawha_uncle') or None,
                  data.get('dawha_jeddah') or None,
                  data.get('dawha_car') or None,
                  now, user_id))
        else:
            db.execute("""
                INSERT INTO phase1_predictions
                    (user_id, group_picks, total_goals, golden_boot,
                     golden_boot_2, golden_boot_3,
                     golden_ball, golden_ball_2, golden_ball_3,
                     dark_horse, wildcard, champion_p1,
                     dawha_ronaldo, dawha_bulga_goals, dawha_uncle,
                     dawha_jeddah, dawha_car, submitted_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (user_id, group_picks_json,
                  data.get('total_goals'),
                  data.get('golden_boot') or None,
                  data.get('golden_boot_2') or None,
                  data.get('golden_boot_3') or None,
                  data.get('golden_ball') or None,
                  data.get('golden_ball_2') or None,
                  data.get('golden_ball_3') or None,
                  data.get('dark_horse') or None,
                  data.get('wildcard') or None,
                  data.get('champion_p1') or None,
                  data.get('dawha_ronaldo') or None,
                  data.get('dawha_bulga_goals'),
                  data.get('dawha_uncle') or None,
                  data.get('dawha_jeddah') or None,
                  data.get('dawha_car') or None,
                  now, now))
        db.commit()


def set_wildcard_pts(user_id, pts):
    with get_db() as db:
        db.execute(
            'UPDATE phase1_predictions SET wildcard_pts = ? WHERE user_id = ?',
            (int(pts), user_id)
        )
        db.commit()


def get_phase2_fixtures():
    """Return list of 16 R32 fixtures [{match_num, home, away}] from results table."""
    results = get_all_results()
    return [
        {
            'match_num': i,
            'home': results.get(f'p2_fixture_{i}_home') or '',
            'away': results.get(f'p2_fixture_{i}_away') or '',
        }
        for i in range(1, 17)
    ]


def set_dawha_pts(user_id, pts):
    with get_db() as db:
        db.execute(
            'UPDATE phase1_predictions SET dawha_pts = ? WHERE user_id = ?',
            (int(pts), user_id)
        )
        db.commit()


# ── Phase 2 predictions ────────────────────────────────────────────────────

def get_phase2_prediction(user_id):
    with get_db() as db:
        row = db.execute(
            'SELECT * FROM phase2_predictions WHERE user_id = ?', (user_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    for key in ('r32_winners', 'quarterfinalists', 'semifinalists', 'finalists'):
        d[key] = json.loads(d[key] or '[]')
    return d


def save_phase2_prediction(user_id, data: dict):
    """
    data keys: r32_winners (list), quarterfinalists (list),
               semifinalists (list), finalists (list), champion,
               final_home_goals, final_away_goals, penalties_count,
               golden_boot
    """
    def jdump(v):
        return json.dumps(v or [], ensure_ascii=False)

    now = datetime.utcnow().isoformat(timespec='seconds')
    with get_db() as db:
        existing = db.execute(
            'SELECT id FROM phase2_predictions WHERE user_id = ?', (user_id,)
        ).fetchone()
        if existing:
            db.execute("""
                UPDATE phase2_predictions
                SET r32_winners=?, quarterfinalists=?, semifinalists=?,
                    finalists=?, champion=?, final_home_goals=?,
                    final_away_goals=?, dark_horse=?, updated_at=?
                WHERE user_id=?
            """, (jdump(data.get('r32_winners')),
                  jdump(data.get('quarterfinalists')),
                  jdump(data.get('semifinalists')),
                  jdump(data.get('finalists')),
                  data.get('champion') or None,
                  data.get('final_home_goals'),
                  data.get('final_away_goals'),
                  data.get('dark_horse') or None,
                  now, user_id))
        else:
            db.execute("""
                INSERT INTO phase2_predictions
                    (user_id, r32_winners, quarterfinalists, semifinalists,
                     finalists, champion, final_home_goals, final_away_goals,
                     dark_horse, submitted_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (user_id,
                  jdump(data.get('r32_winners')),
                  jdump(data.get('quarterfinalists')),
                  jdump(data.get('semifinalists')),
                  jdump(data.get('finalists')),
                  data.get('champion') or None,
                  data.get('final_home_goals'),
                  data.get('final_away_goals'),
                  data.get('dark_horse') or None,
                  now, now))
        db.commit()


# ── Phase 3 predictions ────────────────────────────────────────────────────

def get_phase3_prediction(user_id):
    with get_db() as db:
        row = db.execute(
            'SELECT * FROM phase3_predictions WHERE user_id = ?', (user_id,)
        ).fetchone()
    return dict(row) if row else None


def save_phase3_prediction(user_id, data: dict):
    now = datetime.utcnow().isoformat(timespec='seconds')
    with get_db() as db:
        existing = db.execute(
            'SELECT id FROM phase3_predictions WHERE user_id = ?', (user_id,)
        ).fetchone()
        fields = ('final_to_penalties', 'first_scorer', 'more_goals_semi',
                  'exact_final_home', 'exact_final_away', 'red_cards_remaining',
                  'final_goals', 'red_card_final', 'mom_final')
        vals = tuple(data.get(f) or None for f in fields)
        if existing:
            set_clause = ', '.join(f'{f}=?' for f in fields) + ', updated_at=?'
            db.execute(
                f'UPDATE phase3_predictions SET {set_clause} WHERE user_id=?',
                vals + (now, user_id)
            )
        else:
            placeholders = ', '.join('?' * len(fields))
            db.execute(
                f"""INSERT INTO phase3_predictions
                    (user_id, {', '.join(fields)}, submitted_at, updated_at)
                    VALUES (?, {placeholders}, ?, ?)""",
                (user_id,) + vals + (now, now)
            )
        db.commit()


# ── Results ────────────────────────────────────────────────────────────────

def get_result(key):
    with get_db() as db:
        row = db.execute('SELECT value FROM results WHERE key = ?', (key,)).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row['value'])
    except (json.JSONDecodeError, TypeError):
        return row['value']


def set_result(key, value):
    encoded = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    with get_db() as db:
        db.execute(
            'INSERT OR REPLACE INTO results (key, value) VALUES (?, ?)',
            (key, encoded)
        )
        db.commit()


def get_all_results():
    with get_db() as db:
        rows = db.execute('SELECT key, value FROM results').fetchall()
    out = {}
    for row in rows:
        try:
            out[row['key']] = json.loads(row['value'])
        except (json.JSONDecodeError, TypeError):
            out[row['key']] = row['value']
    return out


# ── Activity feed ──────────────────────────────────────────────────────────

def add_activity(message, detail=None, category='info'):
    with get_db() as db:
        db.execute(
            'INSERT INTO activity (message, detail, category) VALUES (?, ?, ?)',
            (message, detail, category)
        )
        db.commit()


def get_recent_activity(limit=8):
    with get_db() as db:
        return db.execute(
            'SELECT * FROM activity ORDER BY created_at DESC LIMIT ?', (limit,)
        ).fetchall()


# ── Phase 1 completion helper ──────────────────────────────────────────────

def phase1_completion(pred, groups):
    """Return (filled_count, total_required, pct) for the progress ring."""
    # required: winner+runner per group + golden_boot + total_goals + champion_p1
    total = len(groups) * 2 + 3
    if not pred:
        return 0, total, 0
    filled = 0
    gp = pred.get('group_picks', {})
    for g in groups:
        if gp.get(g, {}).get('winner'):
            filled += 1
        if gp.get(g, {}).get('runner'):
            filled += 1
    if pred.get('golden_boot'):
        filled += 1
    if pred.get('total_goals') is not None:
        filled += 1
    if pred.get('champion_p1'):
        filled += 1
    pct = round(filled / total * 100) if total else 0
    return filled, total, pct
