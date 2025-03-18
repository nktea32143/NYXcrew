from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, cache
from models import SignInRecord, DanceSession, Note
from datetime import date
import json

dashboard = Blueprint('dashboard', __name__)

@cache.cached(timeout=60)  # Cache for 60 seconds
def get_sign_in_records(user_id):
    return SignInRecord.query.filter_by(user_id=user_id).order_by(SignInRecord.sign_in_date.desc()).all()

@cache.cached(timeout=60)
def get_dance_sessions(user_id):
    return DanceSession.query.filter_by(user_id=user_id).order_by(DanceSession.session_date.desc()).all()

@cache.cached(timeout=60)
def get_notes(user_id):
    return Note.query.filter_by(user_id=user_id).order_by(Note.note_date.desc()).all()

@dashboard.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    sign_in_records = get_sign_in_records(current_user.id)
    total_sign_in_days = len(sign_in_records)
    consecutive_sign_in_days = 0
    sign_in_dates = [record.sign_in_date for record in sign_in_records]
    sign_in_dates.sort(reverse=True)
    if sign_in_dates:
        last_sign_in_date = sign_in_dates[0]
        consecutive_sign_in_days = 1
        for i in range(1, len(sign_in_dates)):
            if (last_sign_in_date - sign_in_dates[i]).days == 1:
                consecutive_sign_in_days += 1
            else:
                break
            last_sign_in_date = sign_in_dates[i]

    dance_sessions = get_dance_sessions(current_user.id)
    total_dance_time = sum(session.duration for session in dance_sessions)
    average_dance_time = total_dance_time / len(dance_sessions) if dance_sessions else 0
    today = date.today()
    existing_session = DanceSession.query.filter_by(user_id=current_user.id, session_date=today).first()

    if request.method == 'POST' and 'duration' in request.form and existing_session is None:
        duration = float(request.form['duration'])
        new_session = DanceSession(user_id=current_user.id, duration=duration, session_date=today)
        db.session.add(new_session)
        db.session.commit()
        flash('練舞時間紀錄成功！', 'success')

    if request.method == 'POST' and 'sign_in' in request.form:
        existing_sign_in = SignInRecord.query.filter_by(user_id=current_user.id, sign_in_date=today).first()
        if not existing_sign_in:
            new_sign_in = SignInRecord(user_id=current_user.id, sign_in_date=today)
            db.session.add(new_sign_in)
            db.session.commit()
            flash('簽到成功！', 'success')
        else:
            flash('今天已經簽到過了！', 'warning')

    if request.method == 'POST' and 'note_content' in request.form and 'edit_note_id' not in request.form:
        content = request.form['note_content']
        new_note = Note(user_id=current_user.id, content=content, note_date=today)
        db.session.add(new_note)
        db.session.commit()
        flash('筆記新增成功！', 'success')

    if request.method == 'POST' and 'edit_note_id' in request.form:
        note_id = request.form['edit_note_id']
        note = Note.query.get_or_404(note_id)
        if note.user_id == current_user.id:
            note.content = request.form['note_content']
            db.session.commit()
            flash('筆記更新成功！', 'success')
        else:
            flash('無權編輯此筆記！', 'danger')

    notes = get_notes(current_user.id)
    labels = [str(session.session_date) for session in dance_sessions]
    dance_data = [session.duration for session in dance_sessions]
    labels_json = json.dumps(labels)
    dance_data_json = json.dumps(dance_data)
    today_dance_time = existing_session.duration if existing_session else '尚未提交練舞時間'

    return render_template('dashboard.html',
                         total_sign_in_days=total_sign_in_days,
                         consecutive_sign_in_days=consecutive_sign_in_days,
                         total_dance_time=total_dance_time,
                         average_dance_time=average_dance_time,
                         today_dance_time=today_dance_time,
                         labels=labels_json,
                         dance_data=dance_data_json,
                         notes=notes)

@dashboard.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()
        flash('筆記刪除成功！', 'success')
    else:
        flash('無權刪除此筆記！', 'danger')
    return redirect(url_for('dashboard.dashboard'))