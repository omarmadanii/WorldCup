"""
config.py — app settings, game data, scoring values.
All non-code values live here so edits never touch logic files.
"""
import os

# ── Secrets ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-CHANGE-IN-PROD')
DATABASE    = os.path.join(os.path.dirname(__file__), 'database.db')

# ── Initial admin account (bootstrap only, change after first run) ─────────
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

# ── 2026 FIFA World Cup groups (A – L, 4 teams each) ──────────────────────
# Source: Official FIFA draw, December 5 2025
WC_GROUPS = {
    'A': ['المكسيك', 'جنوب أفريقيا', 'كوريا الجنوبية', 'التشيك'],
    'B': ['كندا', 'سويسرا', 'قطر', 'البوسنة والهرسك'],
    'C': ['البرازيل', 'المغرب', 'هايتي', 'اسكتلندا'],
    'D': ['الولايات المتحدة', 'باراغواي', 'أستراليا', 'تركيا'],
    'E': ['ألمانيا', 'كوراساو', 'كوت ديفوار', 'إكوادور'],
    'F': ['هولندا', 'اليابان', 'السويد', 'تونس'],
    'G': ['بلجيكا', 'مصر', 'إيران', 'نيوزيلندا'],
    'H': ['إسبانيا', 'الرأس الأخضر', 'السعودية', 'الأوروغواي'],
    'I': ['فرنسا', 'السنغال', 'النرويج', 'العراق'],
    'J': ['الأرجنتين', 'الجزائر', 'النمسا', 'الأردن'],
    'K': ['البرتغال', 'الكونغو الديمقراطية', 'أوزبكستان', 'كولومبيا'],
    'L': ['إنجلترا', 'كرواتيا', 'غانا', 'بنما'],
}

# Flat list of all 48 teams (used in selects / datalists)
ALL_TEAMS = sorted({t for group in WC_GROUPS.values() for t in group})

# ── Top players list (Golden Boot / Golden Ball selects) ──────────────────
# ⚠️  Extend with current-squad players before the tournament
TOP_PLAYERS = [
    'كيليان مبابي',
    'إيرلينج هالاند',
    'فينيسيوس جونيور',
    'ليونيل ميسي',
    'لوتارو مارتينيز',
    'هاري كين',
    'رافينيا',
    'أوسمان ديمبيلي',
    'محمد صلاح',
    'رودريغو',
    'فيل فودين',
    'بوكايو صاكا',
    'جود بيلينغهام',
    'ليروي ساني',
    'آنطوان غريزمان',
    'برونو فيرنانديز',
    'رافاييل ليياو',
    'غافي',
    'بيدري',
    'لامين يامال',
]
# dedupe while preserving order
seen = set()
TOP_PLAYERS = [p for p in TOP_PLAYERS if not (p in seen or seen.add(p))]

# ── Scoring values (edit here → scoring.py reads from here) ───────────────
# All values match GAME_RULES.md placeholders — change freely.
SCORES = {
    'group_qualified':      1,   # team makes it to R32 (regardless of position)
    'group_position_bonus': 1,   # extra: position (1st or 2nd) also correct
    'dark_horse':           8,
    'total_goals_exact':   10,
    'total_goals_near':     5,   # within ±5 of actual
    'total_goals_near_range': 5,
    'golden_boot_p1':      10,
    'golden_ball':         10,
    'r32_winner':           3,
    'quarterfinalist':      5,
    'semifinalist':         8,
    'finalist':            10,
    'champion':            20,
    'exact_final_score':   10,
    'penalty_count':        8,
    'golden_boot_p2':      10,
    'chaos_item':           5,
}

# ── Phase names (Arabic display strings) ──────────────────────────────────
PHASE_NAMES = {
    1: 'دور المجموعات',
    2: 'دور الخروج',
    3: 'جولة الفوضى',
}
