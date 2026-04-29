from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_user, logout_user
from urllib.parse import urlparse
from app import db, limiter
from app.forms import LoginForm, RegistrationForm
from app.models import User, Role, LogEntry
from datetime import datetime, timezone
from app.routes.utils import log_security_event # 导入公共函数

bp = Blueprint('auth', __name__)

@bp.before_app_request
def before_request_auth():
    if current_user.is_authenticated:
        current_user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
    log_security_event(f"Request to {request.path}", user_id=current_user.id if current_user.is_authenticated else None)


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute") # Rate limiting for login attempts
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('无效的用户名或密码', 'danger')
            log_security_event(f"Failed login attempt for {form.username.data}", ip_address=request.remote_addr)
            return redirect(url_for('auth.login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')
        flash('登录成功！', 'success')
        log_security_event(f"User {user.username} logged in", user_id=user.id)
        return redirect(next_page)
    return render_template('login.html', title='登录', form=form)

@bp.route('/logout')
def logout():
    if current_user.is_authenticated: # Ensure user is logged in before logging out
        log_security_event(f"User {current_user.username} logged out", user_id=current_user.id)
        logout_user()
        flash('您已成功退出。', 'info')
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("60 per hour") # Rate limiting for registration
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # Assign 'user' role by default
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user')
            db.session.add(user_role)
            db.session.commit()
        user.roles.append(user_role)
        db.session.commit()
        flash('恭喜，您已成功注册！', 'success')
        log_security_event(f"New user registered: {user.username}", user_id=user.id)
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='注册', form=form)