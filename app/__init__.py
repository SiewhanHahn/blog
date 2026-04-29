from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_moment import Moment
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
import os

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address)
moment = Moment()
csrf = CSRFProtect()
admin_ext = Admin(name='博客管理后台')

# 登录配置
login.login_view = 'auth.login'
login.login_message = '请先登录以访问此页面。'
login.login_message_category = 'info'

# 安全的 Flask-Admin 视图模型
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 添加 ProxyFix 以支持 Docker 环境
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bcrypt.init_app(app)
    moment.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # 挂载带有权限校验的 Admin
    admin_ext.init_app(app, index_view=SecureAdminIndexView())

    # 注册蓝图
    from app.routes import main, auth, posts, comments, search, errors, admin, categories
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(posts.bp, url_prefix='/post')
    app.register_blueprint(comments.bp, url_prefix='/comment')
    app.register_blueprint(search.bp, url_prefix='/search')
    app.register_blueprint(errors.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(categories.bp, url_prefix='/category')

    with app.app_context():
        import time
        from sqlalchemy.exc import OperationalError
        from app.models import User, Post, Category, Tag, Comment, Role, LogEntry

        # 优化视图注册逻辑，防止重复加载
        if len(admin_ext._views) <= 1:
            admin_ext.add_view(SecureModelView(User, db.session, name='用户管理'))
            admin_ext.add_view(SecureModelView(Post, db.session, name='文章管理'))
            admin_ext.add_view(SecureModelView(Category, db.session, name='分类管理'))
            admin_ext.add_view(SecureModelView(Tag, db.session, name='标签管理'))
            admin_ext.add_view(SecureModelView(Comment, db.session, name='评论管理'))
            admin_ext.add_view(SecureModelView(LogEntry, db.session, name='系统日志'))

        # 数据库重试机制
        max_retries = 5
        for i in range(max_retries):
            try:
                db.create_all()
                break
            except OperationalError:
                if i == max_retries - 1: raise
                time.sleep(3)

        # 检查并创建管理员
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@blog.com', is_admin=True)
            admin_user.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123_ChangeMe!'))
            db.session.add(admin_user)
            db.session.commit()

        # ======== 核心修复：自动创建默认分类 ========
        if Category.query.count() == 0:
            default_categories = [
                Category(name='技术教程', slug='tech-tutorial'),
                Category(name='生活随笔', slug='life-essay'),
                Category(name='读书笔记', slug='book-notes')
            ]
            for category in default_categories:
                db.session.add(category)
            db.session.commit()
            print("已自动创建默认分类！")
        # ==========================================

    return app