from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date
import json
import logging

# 設置日誌
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # 請替換為安全的隨機值
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Updated User Model with is_admin field
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    sign_in_records = db.relationship('SignInRecord', backref='user', lazy=True)
    dance_sessions = db.relationship('DanceSession', backref='user', lazy=True)
    notes = db.relationship('Note', backref='user', lazy=True)

# SignInRecord Model
class SignInRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sign_in_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# DanceSession Model
class DanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Note Model
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    note_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            flash("登入成功！", "success")
            logging.debug("Login successful, redirecting to dashboard")
            return redirect(url_for("dashboard"))
        else:
            flash("登入失敗，請檢查帳號或密碼", "danger")
            logging.debug("Login failed, rendering home.html")
            return render_template("home.html")
    return render_template("home.html")

# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User(username=username, password=password, is_admin=False)
        db.session.add(user)
        db.session.commit()
        flash("註冊成功！請登入", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# Dashboard Route
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    logging.debug(f"Current user authenticated: {current_user.is_authenticated}")
    sign_in_records = SignInRecord.query.filter_by(user_id=current_user.id).all()
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

    dance_sessions = DanceSession.query.filter_by(user_id=current_user.id).all()
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

    notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.note_date.desc()).all()
    labels = [str(session.session_date) for session in dance_sessions]
    dance_data = [session.duration for session in dance_sessions]
    labels_json = json.dumps(labels)
    dance_data_json = json.dumps(dance_data)
    today_dance_time = existing_session.duration if existing_session else "尚未提交練舞時間"

    return render_template('dashboard.html',
                         total_sign_in_days=total_sign_in_days,
                         consecutive_sign_in_days=consecutive_sign_in_days,
                         total_dance_time=total_dance_time,
                         average_dance_time=average_dance_time,
                         today_dance_time=today_dance_time,
                         labels=labels_json,
                         dance_data=dance_data_json,
                         notes=notes)

# Delete Note Route
@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()
        flash('筆記刪除成功！', 'success')
    else:
        flash('無權刪除此筆記！', 'danger')
    return redirect(url_for('dashboard'))

# Admin Required Decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('此頁面僅限管理員訪問！', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

# Admin Route
@app.route('/admin')
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
        today_dance_time = today_dance_time.duration if today_dance_time else "尚未提交"

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

# Logout Route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password='admin123', is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)