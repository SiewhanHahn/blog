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
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
import os
import hashlib

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address)
moment = Moment()
admin_ext = Admin(name='博客管理后台', template_mode='bootstrap4')

# 登录配置
login.login_view = 'auth.login'
login.login_message = '请先登录以访问此页面。'
login.login_message_category = 'info'


def get_identifier():
    from flask import request
    from flask_login import current_user

    if current_user.is_authenticated:
        return f"user:{current_user.id}"

    user_agent = request.headers.get('User-Agent', '')[:50]
    # 修复：使用 sha256 替代 md5，提升合规性及安全性
    ua_hash = hashlib.sha256(user_agent.encode('utf-8')).hexdigest()[:16]
    identifier = f"ip:{get_remote_address()}:{ua_hash}"
    return identifier


# 安全的 Flask-Admin 视图模型 (仅允许管理员访问)
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

    # 修复：添加 ProxyFix 以支持 Nginx/Docker 环境下正确获取客户端真实 IP
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bcrypt.init_app(app)
    moment.init_app(app)
    limiter.init_app(app)

    # 挂载带有权限校验的 Admin
    admin_ext.init_app(app, index_view=SecureAdminIndexView())

    # 注册自定义错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_error(e):
        from flask import request
        import random
        from app.routes.utils import log_security_event

        if random.random() < 0.1:  # 10%的采样率
            log_security_event(f"Rate limit exceeded: {request.path}",
                               ip_address=request.remote_addr)

        return render_template('errors/429.html',
                               title='访问过于频繁',
                               message='您的访问频率过高，请稍后再试。'), 429

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

        # 动态注册后台管理视图
        if not admin_ext._views:
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
            except OperationalError as e:
                if i == max_retries - 1:
                    print("数据库连接失败，已达到最大重试次数！")
                    raise e
                print(f"数据库未就绪，等待重试 ({i + 1}/{max_retries})...")
                time.sleep(3)

        # 检查并创建管理员 (修复硬编码密码问题)
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@blog.com',
                is_admin=True
            )
            # 通过环境变量传递默认密码，并要求尽快修改
            default_pass = os.environ.get('ADMIN_PASSWORD', 'admin123_ChangeMe!')
            admin_user.set_password(default_pass)
            db.session.add(admin_user)

            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin')
                db.session.add(admin_role)

            user_role = Role.query.filter_by(name='user').first()
            if not user_role:
                user_role = Role(name='user')
                db.session.add(user_role)

            db.session.commit()
            print(f"已自动创建管理员账号: admin / {default_pass} (生产环境请务必修改！)")

        if Category.query.count() == 0:
            categories = [
                Category(name='技术教程', slug='tech-tutorial'),
                Category(name='生活随笔', slug='life-essay'),
                Category(name='读书笔记', slug='book-notes'),
                Category(name='项目分享', slug='project-sharing')
            ]
            for category in categories:
                db.session.add(category)
            db.session.commit()

    @app.cli.command("create-admin")
    def create_admin_command():
        from app.models import User
        username = input("请输入管理员用户名 [admin]: ") or "admin"
        email = input("请输入管理员邮箱 [admin@blog.com]: ") or "admin@blog.com"
        password = input("请输入管理员密码: ")
        if not password:
            print("错误：密码不能为空！")
            return

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            existing_user.is_admin = True
            existing_user.email = email
            existing_user.set_password(password)
            db.session.commit()
            print(f"已将用户 {username} 提升为管理员")
        else:
            admin_user = User(username=username, email=email, is_admin=True)
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"已创建管理员账号: {username}")
        print("管理员账号创建完成！")

    @app.cli.command("list-admins")
    def list_admins_command():
        from app.models import User
        admins = User.query.filter_by(is_admin=True).all()
        if admins:
            print("管理员列表:")
            for admin in admins:
                print(f"- {admin.username} ({admin.email})")
        else:
            print("没有找到管理员账号")

    @app.cli.command("create-sample-data")
    def create_sample_data_command():
        import random
        from datetime import datetime, timedelta
        from app.models import User, Post, Comment, Category, Tag, Role
        print("开始创建样本数据...")
        users_data = [
            {'username': '张三', 'email': 'zhangsan@blog.com', 'is_admin': False},
            {'username': '李四', 'email': 'lisi@blog.com', 'is_admin': False},
            {'username': '王五', 'email': 'wangwu@blog.com', 'is_admin': False},
        ]
        for user_data in users_data:
            user = User.query.filter_by(username=user_data['username']).first()
            if not user:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    is_admin=user_data['is_admin']
                )
                user.set_password('123456')
                db.session.add(user)
        db.session.commit()

        users = User.query.all()
        categories = Category.query.all()
        if users and categories:
            posts_content = [
                {'title': 'Flask Web开发入门指南', 'content': 'Flask是一个轻量级的Python Web框架...',
                 'category': categories[0]},
                {'title': 'Python数据库操作详解', 'content': '在Python中，我们可以使用多种方式...',
                 'category': categories[0]},
                {'title': '我的编程学习之路', 'content': '还记得第一次接触编程是在大学时期...',
                 'category': categories[1]}
            ]
            for post_data in posts_content:
                author = random.choice([u for u in users if u.username != 'admin'])
                post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    author=author,
                    category=post_data['category'],
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.session.add(post)
            db.session.commit()
            print("样本数据创建完成！")
        else:
            print("无法创建样本数据：缺少用户或分类")

    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Post, Comment, Category, Tag, Role, LogEntry
        return {
            'db': db, 'User': User, 'Post': Post, 'Comment': Comment,
            'Category': Category, 'Tag': Tag, 'Role': Role, 'LogEntry': LogEntry
        }

    return app