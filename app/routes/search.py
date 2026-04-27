from flask import Blueprint, render_template, flash, request
from flask_login import current_user
from app import db
from app.forms import SearchForm
from app.models import Post
from sqlalchemy import text  # For SQL Injection demonstration
from app.routes.utils import log_security_event  # 导入公共函数

bp = Blueprint('search', __name__)


class SimplePost:
    """用于SQL注入演示的简单文章类"""

    def __init__(self, row_data):
        self.id = row_data[0]
        self.title = str(row_data[1]) if row_data[1] is not None else 'SQL Injection Result'
        self.content = str(row_data[2]) if row_data[2] is not None else str(row_data[3]) if row_data[
            3] else 'Database Information'
        self.content_html = str(row_data[3]) if row_data[3] is not None else ''
        self.created_at = row_data[4]
        self.author = type('MockUser', (), {'username': 'Database'})()
        self.category = None
        self.tags = []

    @property
    def comments_count(self):
        return 0


@bp.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    posts = []
    if form.validate_on_submit():
        query = form.q.data
        # SQL Injection Vulnerability (Deliberate for demonstration)
        # DON'T USE THIS IN PRODUCTION WITHOUT PROPER SANITIZATION OR PARAMETERIZATION

        try:
            # This is intentionally vulnerable to demonstrate SQL Injection.
            # 故意留有的SQL注入漏洞（用于演示）
            sql_query = f"SELECT * FROM post WHERE title LIKE '%{query}%' OR content LIKE '%{query}%'"
            result = db.session.execute(text(sql_query))

            # 处理查询结果 - 使用SimplePost包装数据
            processed_posts = []
            for row in result:
                # 检查是否是UNION查询的结果（包含数字等特殊数据）
                if any(str(i) in str(row[1]) for i in range(10)) and any(
                        keyword in query.upper() for keyword in ['UNION', 'SELECT', 'DATABASE', 'VERSION']):
                    # 这是SQL注入结果，使用SimplePost包装
                    post_obj = SimplePost(row)
                    processed_posts.append(post_obj)
                else:
                    # 这是正常文章结果，尝试创建Post对象
                    try:
                        post = Post(
                            id=row[0],
                            title=row[1],
                            content=row[2],
                            content_html=row[3],
                            created_at=row[4],
                            updated_at=row[5],
                            user_id=row[6],
                            category_id=row[7]
                        )
                        # 设置作者信息
                        from app.models import User
                        author = User.query.get(row[6])
                        if author:
                            post.author = author
                        processed_posts.append(post)
                    except Exception:
                        # 如果创建Post对象失败，使用SimplePost
                        post_obj = SimplePost(row)
                        processed_posts.append(post_obj)

            posts = processed_posts

            # 根据查询类型显示不同的提示信息
            if any(keyword in query.upper() for keyword in ['UNION', 'SELECT']):
                flash(f"SQL注入演示成功！查询到 {len(posts)} 条结果", 'warning')
            else:
                flash(f"搜索 '{query}' 的结果 (查询到 {len(posts)} 篇文章)", 'info')

            log_security_event(f"Search query: '{query}' (potential SQLi if malicious payload)",
                               user_id=current_user.id if current_user.is_authenticated else None)

        except Exception as e:
            flash(f"搜索失败: {e} (可能受到 SQL 注入攻击)", 'danger')
            log_security_event(f"SQL Injection attempt detected with query: '{query}' - Error: {e}",
                               user_id=current_user.id if current_user.is_authenticated else None,
                               ip_address=request.remote_addr)
            posts = []
    else:
        # If no query, show recent posts or similar
        posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        if not posts:
            flash("目前没有文章可供搜索，请尝试发布一些。", "info")

    return render_template('search.html', title='搜索', form=form, posts=posts)