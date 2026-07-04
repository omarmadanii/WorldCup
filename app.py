"""
app.py — Flask routes. Keep thin; logic lives in models.py / scoring.py.
"""
from functools import wraps

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)

import models
import scoring
from config import WC_GROUPS, ALL_TEAMS, TOP_PLAYERS, PHASE_NAMES, SCORES

app = Flask(__name__)

# Load SECRET_KEY from config (which reads from env)
from config import SECRET_KEY
app.secret_key = SECRET_KEY


# ── Bootstrap DB on import ─────────────────────────────────────────────────
models.init_db()


# ── Auth helpers ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('غير مصرح لك بالوصول.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ── Context processor ──────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    user = None
    if session.get('user_id'):
        user = models.get_user_by_id(session['user_id'])
    phases = models.get_all_phases()
    # Current open/locked phase (the first non-pending one, or the latest)
    current_phase = None
    for ph in phases:
        if ph['status'] in ('open', 'locked'):
            current_phase = ph
    if current_phase is None and phases:
        current_phase = phases[0]  # fallback: phase 1

    return {
        'current_user':  user,
        'all_phases':    phases,
        'current_phase': current_phase,
        'phase_names':   PHASE_NAMES,
        'config_scores': SCORES,
    }


# ── Countdown helper ───────────────────────────────────────────────────────

def _deadline_display(phase):
    """Return (iso_string, display_string) for the phase deadline."""
    if not phase or not phase['deadline']:
        return None, None
    return phase['deadline'], phase['deadline']


# ── Auth routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = models.verify_password(username, password)
        if user:
            session.clear()
            session['user_id']  = user['id']
            session['is_admin'] = bool(user['is_admin'])
            return redirect(url_for('dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'error')
    return render_template('login.html', active_tab=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Dashboard ──────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    uid    = session['user_id']
    phases = models.get_all_phases()

    # Find the currently active phase
    active_phase = next(
        (p for p in phases if p['status'] == 'open'), None
    ) or next(
        (p for p in phases if p['status'] == 'locked'), None
    ) or phases[0]

    deadline_iso, _ = _deadline_display(active_phase)

    # Submission completion for the active phase
    completion = None
    if active_phase['id'] == 1:
        pred = models.get_phase1_prediction(uid)
        filled, total, pct = models.phase1_completion(pred, list(WC_GROUPS.keys()))
        completion = {'filled': filled, 'total': total, 'pct': pct,
                      'missing': _phase1_missing(pred)}
    elif active_phase['id'] == 2:
        pred = models.get_phase2_prediction(uid)
        pct = 100 if (pred and pred.get('champion')) else 0
        completion = {'pct': pct}
    elif active_phase['id'] == 3:
        pred = models.get_phase3_prediction(uid)
        pct = 100 if pred else 0
        completion = {'pct': pct}

    # Leaderboard snapshot — only show once Phase 1 has locked
    p1 = next((p for p in phases if p['id'] == 1), None)
    standings = scoring.get_standings() if (p1 and p1['status'] == 'locked') else []
    top5 = standings[:5]

    # Current user rank
    my_row = next((r for r in standings if r['user']['id'] == uid), None)

    activity = models.get_recent_activity(6)

    return render_template(
        'dashboard.html',
        active_tab='dashboard',
        active_phase=active_phase,
        deadline_iso=deadline_iso,
        completion=completion,
        top5=top5,
        my_row=my_row,
        activity=activity,
    )


def _phase1_missing(pred):
    """Return a short Arabic string listing unfilled required fields."""
    if not pred:
        return 'لم تُقدّم توقعاتك بعد'
    missing = []
    if not pred.get('champion_p1'):
        missing.append('البطل')
    if not pred.get('golden_boot'):
        missing.append('الهداف')
    if pred.get('total_goals') is None:
        missing.append('مجموع الأهداف')
    return ' · '.join(missing) if missing else ''


# ── Phase 1 prediction form ────────────────────────────────────────────────

@app.route('/predict/1', methods=['GET', 'POST'])
@login_required
def predict_phase1():
    uid   = session['user_id']
    phase = models.get_phase(1)

    if request.method == 'POST':
        if phase['status'] == 'locked':
            flash('تم إغلاق توقعات المرحلة الأولى.', 'error')
            return redirect(url_for('predict_phase1'))

        # Build group_picks dict from form
        group_picks = {}
        for letter in WC_GROUPS:
            winner = request.form.get(f'group_{letter}_winner', '').strip()
            runner = request.form.get(f'group_{letter}_runner', '').strip()
            group_picks[letter] = {
                'winner': winner or None,
                'runner': runner or None,
            }

        def _int_field(key):
            try:
                return int(request.form.get(key, ''))
            except (ValueError, TypeError):
                return None

        def _txt(key):
            return request.form.get(key, '').strip() or None

        data = {
            'group_picks':       group_picks,
            'total_goals':       _int_field('total_goals'),
            'champion_p1':       _txt('champion_p1'),
            'golden_boot':       _txt('golden_boot'),
            'golden_boot_2':     _txt('golden_boot_2'),
            'golden_boot_3':     _txt('golden_boot_3'),
            'golden_ball':       _txt('golden_ball'),
            'golden_ball_2':     _txt('golden_ball_2'),
            'golden_ball_3':     _txt('golden_ball_3'),
            'wildcard':          _txt('wildcard'),
            'dawha_ronaldo':     _txt('dawha_ronaldo'),
            'dawha_bulga_goals': _int_field('dawha_bulga_goals'),
            'dawha_uncle':       _txt('dawha_uncle'),
            'dawha_jeddah':      _txt('dawha_jeddah'),
            'dawha_car':         _txt('dawha_car'),
        }
        models.save_phase1_prediction(uid, data)
        flash('تم حفظ توقعاتك بنجاح!', 'success')
        return redirect(url_for('predict_phase1'))

    pred    = models.get_phase1_prediction(uid)
    filled, total, pct = models.phase1_completion(pred, list(WC_GROUPS.keys()))
    deadline_iso, _ = _deadline_display(phase)

    return render_template(
        'predict_phase1.html',
        active_tab='predict',
        phase=phase,
        deadline_iso=deadline_iso,
        groups=WC_GROUPS,
        players=TOP_PLAYERS,
        teams=ALL_TEAMS,
        pred=pred,
        filled=filled,
        total=total,
        pct=pct,
    )


# ── Phase 2 prediction form ────────────────────────────────────────────────

@app.route('/predict/2', methods=['GET', 'POST'])
@login_required
def predict_phase2():
    uid   = session['user_id']
    phase = models.get_phase(2)

    if request.method == 'POST':
        if phase['status'] == 'locked':
            flash('تم إغلاق توقعات المرحلة الثانية.', 'error')
            return redirect(url_for('predict_phase2'))

        def multi(key):
            return [v.strip() for v in request.form.getlist(key) if v.strip()]

        def _int(key):
            try:
                return int(request.form.get(key, ''))
            except (ValueError, TypeError):
                return None

        data = {
            'r32_winners':      multi('r32_winners'),
            'quarterfinalists': multi('quarterfinalists'),
            'semifinalists':    multi('semifinalists'),
            'finalists':        multi('finalists'),
            'champion':         request.form.get('champion', '').strip() or None,
            'final_home_goals': _int('final_home_goals'),
            'final_away_goals': _int('final_away_goals'),
            'dark_horse':       request.form.get('dark_horse', '').strip() or None,
        }
        models.save_phase2_prediction(uid, data)
        flash('تم حفظ توقعاتك بنجاح!', 'success')
        return redirect(url_for('predict_phase2'))

    pred = models.get_phase2_prediction(uid)
    deadline_iso, _ = _deadline_display(phase)
    fixtures = models.get_phase2_fixtures()

    return render_template(
        'predict_phase2.html',
        active_tab='predict',
        phase=phase,
        deadline_iso=deadline_iso,
        fixtures=fixtures,
        teams=ALL_TEAMS,
        players=TOP_PLAYERS,
        pred=pred,
    )


# ── Phase 3 prediction form ────────────────────────────────────────────────

@app.route('/predict/3', methods=['GET', 'POST'])
@login_required
def predict_phase3():
    uid   = session['user_id']
    phase = models.get_phase(3)

    if request.method == 'POST':
        if phase['status'] == 'locked':
            flash('تم إغلاق جولة الفوضى.', 'error')
            return redirect(url_for('predict_phase3'))

        ftp_raw = request.form.get('final_to_penalties', '')
        ftp = 1 if ftp_raw == '1' else (0 if ftp_raw == '0' else None)

        def _int3(key):
            try:
                return int(request.form.get(key, ''))
            except (ValueError, TypeError):
                return None

        rc_raw = request.form.get('red_card_final', '')
        red_card_final = 1 if rc_raw == '1' else (0 if rc_raw == '0' else None)

        data = {
            'final_to_penalties': ftp,
            'first_scorer':       request.form.get('first_scorer', '').strip() or None,
            'final_goals':        _int3('final_goals'),
            'red_card_final':     red_card_final,
            'mom_final':          request.form.get('mom_final', '').strip() or None,
        }
        models.save_phase3_prediction(uid, data)
        flash('تم حفظ توقعاتك بنجاح!', 'success')
        return redirect(url_for('predict_phase3'))

    pred = models.get_phase3_prediction(uid)
    deadline_iso, _ = _deadline_display(phase)

    return render_template(
        'predict_phase3.html',
        active_tab='predict',
        phase=phase,
        deadline_iso=deadline_iso,
        pred=pred,
        players=TOP_PLAYERS,
    )


# ── Leaderboard ────────────────────────────────────────────────────────────

@app.route('/leaderboard')
@login_required
def leaderboard():
    uid    = session['user_id']
    phases = models.get_all_phases()
    p1 = next((p for p in phases if p['id'] == 1), None)
    locked = p1 and p1['status'] == 'locked'

    standings = scoring.get_standings() if locked else []
    my_row = next((r for r in standings if r['user']['id'] == uid), None)
    activity = models.get_recent_activity(10)

    return render_template(
        'leaderboard.html',
        active_tab='board',
        standings=standings,
        my_row=my_row,
        locked=locked,
        activity=activity,
    )


# ── Admin: players ─────────────────────────────────────────────────────────

@app.route('/admin/players', methods=['GET', 'POST'])
@admin_required
def admin_players():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            if not username or not password:
                flash('يرجى إدخال اسم المستخدم وكلمة المرور.', 'error')
            elif models.get_user_by_username(username):
                flash('اسم المستخدم موجود مسبقًا.', 'error')
            else:
                models.create_user(username, password)
                flash(f'تم إنشاء الحساب: {username}', 'success')

        elif action == 'reset_password':
            user_id  = int(request.form.get('user_id', 0))
            new_pass = request.form.get('new_password', '').strip()
            if not new_pass:
                flash('يرجى إدخال كلمة المرور الجديدة.', 'error')
            else:
                models.set_password(user_id, new_pass)
                flash('تم إعادة تعيين كلمة المرور.', 'success')

        elif action == 'set_wildcard':
            user_id = int(request.form.get('user_id', 0))
            pts = request.form.get('wildcard_pts', 0)
            models.set_wildcard_pts(user_id, pts)
            flash('تم تحديث نقاط الرابحة.', 'success')

        elif action == 'set_dawha':
            user_id = int(request.form.get('user_id', 0))
            pts = request.form.get('dawha_pts', 0)
            models.set_dawha_pts(user_id, pts)
            flash('تم تحديث نقاط اختبار الدهاء.', 'success')

        return redirect(url_for('admin_players'))

    users = models.list_users(include_admin=False)
    # Attach their phase1 prediction (for wildcard + dawha display)
    player_data = []
    for u in users:
        p1 = models.get_phase1_prediction(u['id'])
        player_data.append({
            'user': dict(u),
            # Phase 1 key predictions (read-only, auto-scored)
            'champion_p1':   p1.get('champion_p1') if p1 else None,
            'golden_boot':   p1.get('golden_boot') if p1 else None,
            'golden_boot_2': p1.get('golden_boot_2') if p1 else None,
            'golden_boot_3': p1.get('golden_boot_3') if p1 else None,
            'golden_ball':   p1.get('golden_ball') if p1 else None,
            'golden_ball_2': p1.get('golden_ball_2') if p1 else None,
            'golden_ball_3': p1.get('golden_ball_3') if p1 else None,
            # Wildcard + dawha (admin-scored)
            'wildcard': p1.get('wildcard') if p1 else None,
            'wildcard_pts': p1.get('wildcard_pts', 0) if p1 else 0,
            'dawha_ronaldo':     p1.get('dawha_ronaldo') if p1 else None,
            'dawha_bulga_goals': p1.get('dawha_bulga_goals') if p1 else None,
            'dawha_uncle':       p1.get('dawha_uncle') if p1 else None,
            'dawha_jeddah':      p1.get('dawha_jeddah') if p1 else None,
            'dawha_car':         p1.get('dawha_car') if p1 else None,
            'dawha_pts':         p1.get('dawha_pts', 0) if p1 else 0,
        })

    return render_template(
        'admin/players.html',
        active_tab='admin',
        player_data=player_data,
    )


# ── Admin: bonuses / penalties ─────────────────────────────────────────────

@app.route('/admin/bonuses', methods=['GET', 'POST'])
@admin_required
def admin_bonuses():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_bonus':
            user_id = int(request.form.get('user_id', 0))
            note    = request.form.get('note', '').strip()
            try:
                pts = int(request.form.get('points', ''))
            except (ValueError, TypeError):
                pts = 0
            if not user_id or pts == 0:
                flash('يرجى اختيار اللاعب وإدخال عدد نقاط غير صفري.', 'error')
            else:
                models.add_bonus(user_id, pts, note)
                scoring.snapshot_and_refresh()
                sign = '+' if pts > 0 else ''
                flash(f'تمت إضافة {sign}{pts} نقطة.', 'success')

        elif action == 'delete_bonus':
            bonus_id = int(request.form.get('bonus_id', 0))
            if bonus_id:
                models.delete_bonus(bonus_id)
                scoring.snapshot_and_refresh()
                flash('تم حذف التعديل.', 'success')

        return redirect(url_for('admin_bonuses'))

    users = models.list_users(include_admin=False)
    player_data = []
    for u in users:
        adjustments = models.list_bonuses(u['id'])
        player_data.append({
            'user':        dict(u),
            'adjustments': adjustments,
            'bonus_total': sum(b['points'] for b in adjustments),
        })

    return render_template(
        'admin/bonuses.html',
        active_tab='admin',
        player_data=player_data,
    )


# ── Admin: results ─────────────────────────────────────────────────────────

@app.route('/admin/results', methods=['GET', 'POST'])
@admin_required
def admin_results():
    phases = models.get_all_phases()

    if request.method == 'POST':
        action = request.form.get('action', '')

        # Phase status toggle
        if action.startswith('phase_'):
            parts = action.split('_')   # phase_<n>_<status>
            phase_num = int(parts[1])
            new_status = parts[2]
            deadline = request.form.get(f'deadline_{phase_num}', '').strip()
            models.set_phase_status(phase_num, new_status)
            if deadline:
                models.set_phase_deadline(phase_num, deadline)
            flash(f'تم تحديث حالة المرحلة {phase_num}.', 'success')
            models.add_activity(
                f'تغيّرت حالة المرحلة {phase_num} إلى: {new_status}',
                category='info'
            )

        # Save Phase 1 results
        elif action == 'save_p1':
            for letter in 'ABCDEFGHIJKL':
                w = request.form.get(f'p1_group_{letter}_winner', '').strip()
                r = request.form.get(f'p1_group_{letter}_runner', '').strip()
                if w:
                    models.set_result(f'p1_group_{letter.lower()}_winner', w)
                if r:
                    models.set_result(f'p1_group_{letter.lower()}_runner', r)

            for key in ('p1_total_goals', 'p1_golden_boot', 'p1_golden_ball', 'p1_champion'):
                v = request.form.get(key, '').strip()
                if v:
                    models.set_result(key, v)

            scoring.snapshot_and_refresh()
            models.add_activity('تم تحديث نتائج دور المجموعات', category='result')
            flash('تم حفظ نتائج المرحلة الأولى.', 'success')

        # Save Phase 2 R32 fixtures
        elif action == 'save_p2_fixtures':
            for i in range(1, 17):
                home = request.form.get(f'fixture_{i}_home', '').strip()
                away = request.form.get(f'fixture_{i}_away', '').strip()
                if home:
                    models.set_result(f'p2_fixture_{i}_home', home)
                if away:
                    models.set_result(f'p2_fixture_{i}_away', away)
            flash('تم حفظ مباريات دور الـ32.', 'success')
            models.add_activity('تم إدخال مباريات دور الـ32', category='info')

        # Save Phase 2 results
        elif action == 'save_p2':
            def _list_from_textarea(key):
                raw = request.form.get(key, '')
                return [l.strip() for l in raw.splitlines() if l.strip()]

            models.set_result('p2_r32_winners',      _list_from_textarea('p2_r32_winners'))
            models.set_result('p2_quarterfinalists',  _list_from_textarea('p2_quarterfinalists'))
            models.set_result('p2_semifinalists',     _list_from_textarea('p2_semifinalists'))
            models.set_result('p2_finalists',         _list_from_textarea('p2_finalists'))

            for key in ('p2_champion', 'p2_dark_horse'):
                v = request.form.get(key, '').strip()
                if v:
                    models.set_result(key, v)

            for key in ('p2_final_home', 'p2_final_away'):
                v = request.form.get(key, '').strip()
                if v:
                    try:
                        models.set_result(key, int(v))
                    except ValueError:
                        pass

            scoring.snapshot_and_refresh()
            models.add_activity('تم تحديث نتائج دور الخروج', category='result')
            flash('تم حفظ نتائج المرحلة الثانية.', 'success')

        # Save Phase 3 results
        elif action == 'save_p3':
            ftp = request.form.get('p3_final_to_penalties', '')
            if ftp in ('0', '1'):
                models.set_result('p3_final_to_penalties', int(ftp))

            for key in ('p3_first_scorer', 'p3_mom_final'):
                v = request.form.get(key, '').strip()
                if v:
                    models.set_result(key, v)

            ftp3 = request.form.get('p3_red_card_final', '')
            if ftp3 in ('0', '1'):
                models.set_result('p3_red_card_final', int(ftp3))

            v = request.form.get('p3_final_goals', '').strip()
            if v:
                try:
                    models.set_result('p3_final_goals', int(v))
                except ValueError:
                    pass

            scoring.snapshot_and_refresh()
            models.add_activity('تم تحديث نتائج جولة الفوضى', category='result')
            flash('تم حفظ نتائج المرحلة الثالثة.', 'success')

        elif action == 'recalculate':
            scoring.snapshot_and_refresh()
            flash('تم إعادة حساب النقاط.', 'success')

        return redirect(url_for('admin_results'))

    results  = models.get_all_results()
    activity = models.get_recent_activity(10)
    groups   = list('ABCDEFGHIJKL')
    fixtures = models.get_phase2_fixtures()

    return render_template(
        'admin/results.html',
        active_tab='admin',
        phases=phases,
        results=results,
        activity=activity,
        groups=groups,
        teams=ALL_TEAMS,
        players=TOP_PLAYERS,
        groups_dict=WC_GROUPS,
        fixtures=fixtures,
    )


# ── Rules page ────────────────────────────────────────────────────────────

@app.route('/rules')
@login_required
def rules():
    return render_template('rules.html', active_tab='rules')


# ── Dev entry point ────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)
