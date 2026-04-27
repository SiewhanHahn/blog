# app/routes/admin.py
from flask import Blueprint, render_template, flash, abort
from flask_login import current_user, login_required
from app.models import User, Post, LogEntry

# Renamed to admin_routes to avoid conflict with admin variable in __init__.py
bp = Blueprint('admin_routes', __name__) # 蓝图对象名为 bp，内部名称为 'admin_routes'


@bp.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('您没有权限访问管理仪表盘。', 'danger')
        abort(403)

    total_users = User.query.count()
    total_posts = Post.query.count()
    recent_logs = LogEntry.query.order_by(LogEntry.timestamp.desc()).limit(10).all()

    return render_template('admin/index.html',
                           title='管理仪表盘',
                           total_users=total_users,
                           total_posts=total_posts,
                           recent_logs=recent_logs)
