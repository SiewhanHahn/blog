from flask import Blueprint, render_template, flash, request
from flask_login import current_user
from app import db
from app.forms import SearchForm
from app.models import Post
from app.routes.utils import log_security_event

bp = Blueprint('search', __name__)


@bp.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    posts = []

    if form.validate_on_submit():
        query = form.q.data
        try:
            # 修复：使用 SQLAlchemy ORM 防止 SQL 注入
            posts = Post.query.filter(
                Post.title.ilike(f'%{query}%') | Post.content.ilike(f'%{query}%')
            ).all()

            flash(f"搜索 '{query}' 的结果 (查询到 {len(posts)} 篇文章)", 'info')

            log_security_event(f"Search query: '{query}'",
                               user_id=current_user.id if current_user.is_authenticated else None)

        except Exception as e:
            flash(f"搜索失败: 系统遇到意外错误", 'danger')
            log_security_event(f"Search error with query: '{query}' - Error: {e}",
                               user_id=current_user.id if current_user.is_authenticated else None,
                               ip_address=request.remote_addr)
            posts = []
    else:
        # 如果没有查询词，显示最新文章
        posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        if not posts:
            flash("目前没有文章可供搜索，请尝试发布一些。", "info")

    return render_template('search.html', title='搜索', form=form, posts=posts)