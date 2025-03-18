from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from database import db
from models import User, SignInRecord, DanceSession, Note
from datetime import date
import json

admin = Blueprint('admin', __name__)

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('此頁面僅限管理員訪問！', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

@admin.route('/')
@admin_required
def admin_dashboard():
    users = User.query.all()
    user_data = []

    for user in users:
        sign_in_records = SignInRecord.query.filter_by(user_id=user.id).all()
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

        dance_sessions = DanceSession.query.filter_by(user_id=user.id).all()
        total_dance_time = sum(session.duration for session in dance_sessions)
        average_dance_time = total_dance_time / len(dance_sessions) if dance_sessions else 0
        today = date.today()
        today_dance_time = DanceSession.query.filter_by(user_id=user.id, session_date=today).first()
        today_dance_time = today_dance_time.duration if today_dance_time else '尚未提交'

        notes = Note.query.filter_by(user_id=user.id).order_by(Note.note_date.desc()).all()
        labels = [str(session.session_date) for session in dance_sessions]
        dance_data = [session.duration for session in dance_sessions]

        user_data.append({
            'username': user.username,
            'total_sign_in_days': total_sign_in_days,
            'consecutive_sign_in_days': consecutive_sign_in_days,
            'total_dance_time': total_dance_time,
            'average_dance_time': average_dance_time,
            'today_dance_time': today_dance_time,
            'notes': notes,
            'labels': json.dumps(labels),
            'dance_data': json.dumps(dance_data)
        })

    return render_template('admin.html', users=user_data)