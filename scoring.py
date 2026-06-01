"""
scoring.py — always recompute standings fresh from DB.
Never patch totals in-place. Call get_standings() to get the full table.
"""
import models
from config import SCORES, WC_GROUPS


# ── Helpers ────────────────────────────────────────────────────────────────

def _in_list(item, lst):
    """Case-insensitive membership test (handles None safely)."""
    if not item or not lst:
        return False
    return item.strip() in [x.strip() for x in lst if x]


def _int_or_none(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ── Per-phase score functions ──────────────────────────────────────────────

def compute_phase1_score(user_id, results: dict) -> int:
    pred = models.get_phase1_prediction(user_id)
    if not pred:
        return 0

    score = 0
    gp = pred.get('group_picks', {})

    # Group winners / runners
    for letter in WC_GROUPS:
        real_winner = results.get(f'p1_group_{letter.lower()}_winner')
        real_runner = results.get(f'p1_group_{letter.lower()}_runner')
        pick = gp.get(letter, {})

        if real_winner and pick.get('winner') == real_winner:
            score += SCORES['group_winner']
        if real_runner and pick.get('runner') == real_runner:
            score += SCORES['group_runner']

    # Total goals
    real_goals = _int_or_none(results.get('p1_total_goals'))
    pred_goals = _int_or_none(pred.get('total_goals'))
    if real_goals is not None and pred_goals is not None:
        diff = abs(real_goals - pred_goals)
        if diff == 0:
            score += SCORES['total_goals_exact']
        elif diff <= SCORES['total_goals_near_range']:
            score += SCORES['total_goals_near']

    # Golden Boot
    real_boot = results.get('p1_golden_boot')
    if real_boot and pred.get('golden_boot') == real_boot:
        score += SCORES['golden_boot_p1']

    # Golden Ball
    real_ball = results.get('p1_golden_ball')
    if real_ball and pred.get('golden_ball') == real_ball:
        score += SCORES['golden_ball']

    # Dark horse
    real_dark = results.get('p1_dark_horse')
    if real_dark and pred.get('dark_horse') == real_dark:
        score += SCORES['dark_horse']

    # Wildcard (admin-assigned points stored directly on the prediction row)
    score += int(pred.get('wildcard_pts') or 0)

    return score


def compute_phase2_score(user_id, results: dict) -> int:
    pred = models.get_phase2_prediction(user_id)
    if not pred:
        return 0

    score = 0

    # R32 winners (each correct team +3)
    real_r32 = results.get('p2_r32_winners') or []
    for team in pred.get('r32_winners', []):
        if _in_list(team, real_r32):
            score += SCORES['r32_winner']

    # Quarterfinalists (+5 each)
    real_qf = results.get('p2_quarterfinalists') or []
    for team in pred.get('quarterfinalists', []):
        if _in_list(team, real_qf):
            score += SCORES['quarterfinalist']

    # Semifinalists (+8 each)
    real_sf = results.get('p2_semifinalists') or []
    for team in pred.get('semifinalists', []):
        if _in_list(team, real_sf):
            score += SCORES['semifinalist']

    # Finalists (+10 each)
    real_fin = results.get('p2_finalists') or []
    for team in pred.get('finalists', []):
        if _in_list(team, real_fin):
            score += SCORES['finalist']

    # Champion (+20)
    real_champ = results.get('p2_champion')
    if real_champ and pred.get('champion') == real_champ:
        score += SCORES['champion']

    # Exact final score (+25)
    r_home = _int_or_none(results.get('p2_final_home'))
    r_away = _int_or_none(results.get('p2_final_away'))
    p_home = _int_or_none(pred.get('final_home_goals'))
    p_away = _int_or_none(pred.get('final_away_goals'))
    if None not in (r_home, r_away, p_home, p_away):
        if r_home == p_home and r_away == p_away:
            score += SCORES['exact_final_score']

    # Penalty count (+8)
    r_pen = _int_or_none(results.get('p2_penalties_count'))
    p_pen = _int_or_none(pred.get('penalties_count'))
    if r_pen is not None and r_pen == p_pen:
        score += SCORES['penalty_count']

    # Golden Boot phase 2 (+10)
    r_boot2 = results.get('p2_golden_boot')
    if r_boot2 and pred.get('golden_boot') == r_boot2:
        score += SCORES['golden_boot_p2']

    return score


def compute_phase3_score(user_id, results: dict) -> int:
    pred = models.get_phase3_prediction(user_id)
    if not pred:
        return 0

    score = 0
    S = SCORES['chaos_item']

    # Will the final go to penalties?
    r_pen = results.get('p3_final_to_penalties')
    if r_pen is not None and pred.get('final_to_penalties') is not None:
        if int(pred['final_to_penalties']) == int(r_pen):
            score += S

    # First scorer
    r_scorer = results.get('p3_first_scorer')
    if r_scorer and pred.get('first_scorer') == r_scorer:
        score += S

    # Which semifinal has more goals?
    r_semi = results.get('p3_more_goals_semi')
    if r_semi and pred.get('more_goals_semi') == r_semi:
        score += S

    # Exact chaos final score
    r_h = _int_or_none(results.get('p3_exact_final_home'))
    r_a = _int_or_none(results.get('p3_exact_final_away'))
    p_h = _int_or_none(pred.get('exact_final_home'))
    p_a = _int_or_none(pred.get('exact_final_away'))
    if None not in (r_h, r_a, p_h, p_a) and r_h == p_h and r_a == p_a:
        score += S

    # Total red cards remaining
    r_rc = _int_or_none(results.get('p3_red_cards_remaining'))
    p_rc = _int_or_none(pred.get('red_cards_remaining'))
    if r_rc is not None and r_rc == p_rc:
        score += S

    return score


# ── Standings ──────────────────────────────────────────────────────────────

def get_standings():
    """
    Recompute every user's score from stored predictions + results.
    Returns a list of dicts sorted by total (desc), including rank and
    rank-movement vs. the prev_rank stored in the users table.
    """
    results = models.get_all_results()
    users   = models.list_users(include_admin=False)

    rows = []
    for user in users:
        uid = user['id']
        p1  = compute_phase1_score(uid, results)
        p2  = compute_phase2_score(uid, results)
        p3  = compute_phase3_score(uid, results)
        rows.append({
            'user':      dict(user),
            'phase1':    p1,
            'phase2':    p2,
            'phase3':    p3,
            'total':     p1 + p2 + p3,
            'prev_rank': user['prev_rank'] or 0,
        })

    rows.sort(key=lambda r: r['total'], reverse=True)

    for i, row in enumerate(rows, start=1):
        row['rank'] = i
        prev = row['prev_rank']
        if prev == 0:
            row['movement'] = 'new'
        elif prev > i:
            row['movement'] = 'up'
        elif prev < i:
            row['movement'] = 'down'
        else:
            row['movement'] = 'same'
        row['rank_delta'] = abs(prev - i) if prev else 0

    return rows


def snapshot_and_refresh():
    """
    Called by admin after entering results.
    1. Snapshot current ranks into prev_rank.
    2. Recompute standings (returned for convenience).
    """
    current = get_standings()
    models.snapshot_ranks({r['user']['id']: r['rank'] for r in current})
    return get_standings()
