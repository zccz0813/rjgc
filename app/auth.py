# app/auth.py - 认证模块
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import user_model

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = user_model.authenticate(username, password)

        if user and user['status'] == 0:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['real_name'] = user['real_name']
            session['role'] = user['role']
            flash(f'欢迎回来，{user["real_name"]}！', 'success')

            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('books.list'))
        else:
            flash('用户名或密码错误，或账号已被冻结', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('已成功退出登录', 'info')
    return redirect(url_for('auth.login'))