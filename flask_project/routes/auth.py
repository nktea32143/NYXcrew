from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from database import db
from models import User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('登入成功！', 'success')
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('登入失敗，請檢查帳號或密碼', 'danger')
    return render_template('home.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('用戶名已存在！', 'danger')
        else:
            user = User(username=username, is_admin=False)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('註冊成功！請登入', 'success')
            return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))