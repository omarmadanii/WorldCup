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

    # Group qualifiers: +1 if team makes R32, +1 bonus if exact position correct
    for letter in WC_GROUPS:
        real_winner = results.get(f'p1_group_{letter.lower()}_winner')
        real_runner = results.get(f'p1_group_{letter.lower()}_runner')
        pick = gp.get(letter, {})

        for picked, exact_match in [
            (pick.get('winner'), real_winner),
            (pick.get('runner'), real_runner),
        ]:
            if not picked:
                continue
            if picked == real_winner or picked == real_runner:
                score += SCORES['group_qualified']
                if picked == exact_match:
                    score += SCORES['group_position_bonus']

    # Total goals
    real_goals = _int_or_none(results.get('p1_total_goals'))
    pred_goals = _int_or_none(pred.get('total_goals'))
    if real_goals is not None and pred_goals is not None:
        diff = abs(real_goals - pred_goals)
        if diff == 0:
            score += SCORES['total_goals_exact']
        elif diff <= SCORES['total_goals_near_range']:
            score += SCORES['total_goals_near']

    # Champion (predicted in Phase 1)
    real_champ_p1 = results.get('p1_champion')
    if real_champ_p1 and pred.get('champion_p1') == real_champ_p1:
        score += SCORES['champion_p1']

    # Golden Boot — 3 ranked choices (10 / 7 / 5)
    real_boot = results.get('p1_golden_boot')
    if real_boot:
        for choice, pts_key in [
            (pred.get('golden_boot'),   'golden_boot_p1'),
            (pred.get('golden_boot_2'), 'golden_boot_p1_2'),
            (pred.get('golden_boot_3'), 'golden_boot_p1_3'),
        ]:
            if choice and choice.strip() == real_boot.strip():
                score += SCORES[pts_key]
                break

    # Golden Ball — 3 ranked choices (10 / 7 / 5)
    real_ball = results.get('p1_golden_ball')
    if real_ball:
        for choice, pts_key in [
            (pred.get('golden_ball'),   'golden_ball'),
            (pred.get('golden_ball_2'), 'golden_ball_2'),
            (pred.get('golden_ball_3'), 'golden_ball_3'),
        ]:
            if choice and choice.strip() == real_ball.strip():
                score += SCORES[pts_key]
                break


    # Wildcard (admin-assigned points stored directly on the prediction row)
    score += int(pred.get('wildcard_pts') or 0)

    # اختبار الدهاء (admin-assigned, max 10)
    score += int(pred.get('dawha_pts') or 0)

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

    # Dark horse (reaches QF minimum — moved from Phase 1)
    real_dark = results.get('p2_dark_horse')
    if real_dark and pred.get('dark_horse') == real_dark:
        score += SCORES['dark_horse']

    # Exact final score
    r_home = _int_or_none(results.get('p2_final_home'))
    r_away = _int_or_none(results.get('p2_final_away'))
    p_home = _int_or_none(pred.get('final_home_goals'))
    p_away = _int_or_none(pred.get('final_away_goals'))
    if None not in (r_home, r_away, p_home, p_away):
        if r_home == p_home and r_away == p_away:
            score += SCORES['exact_final_score']

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

    # Total goals in the final
    r_fg = _int_or_none(results.get('p3_final_goals'))
    p_fg = _int_or_none(pred.get('final_goals'))
    if r_fg is not None and r_fg == p_fg:
        score += S

    # Red card in the final
    r_rc = results.get('p3_red_card_final')
    if r_rc is not None and pred.get('red_card_final') is not None:
        if int(pred['red_card_final']) == int(r_rc):
            score += S

    # Man of the match
    r_mom = results.get('p3_mom_final')
    if r_mom and pred.get('mom_final'):
        if pred['mom_final'].strip() == r_mom.strip():
            score += S

    return score


# ── Standings ──────────────────────────────────────────────────────────────

def get_standings():
    """
    Recompute every user's score from stored predictions + results.
    Returns a list of dicts sorted by total (desc), including rank and
    rank-movement vs. the prev_rank stored in the users table.
    """
    results  = models.get_all_results()
    users    = models.list_users(include_admin=False)
    bonuses  = models.get_all_bonuses()

    rows = []
    for user in users:
        uid = user['id']
        p1  = compute_phase1_score(uid, results)
        p2  = compute_phase2_score(uid, results)
        p3  = compute_phase3_score(uid, results)
        adjustments = bonuses.get(uid, [])
        bonus = sum(b['points'] for b in adjustments)
        rows.append({
            'user':        dict(user),
            'phase1':      p1,
            'phase2':      p2,
            'phase3':      p3,
            'bonus':       bonus,
            'adjustments': [dict(b) for b in adjustments],
            'total':       p1 + p2 + p3 + bonus,
            'prev_rank':   user['prev_rank'] or 0,
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
