from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_moment import Moment
from config import Config
import os

# 初始化扩展
db = SQLAlchemy()  # 数据库
migrate = Migrate()  # 数据库迁移
login = LoginManager()  # 用户认证管理
bcrypt = Bcrypt()  # 密码加密
limiter = Limiter(key_func=get_remote_address)  # API速率限制
moment = Moment()  # 日期处理

# 登录配置
login.login_view = 'auth.login'
login.login_message = '请先登录以访问此页面。'
login.login_message_category = 'info'


def get_identifier():
    """
    已登录用户按照用户ID限流
    未登录用户按照IP+用户代理限流，防止同一IP多设备绕过限制
    """
    from flask import request
    from flask_login import current_user

    if current_user.is_authenticated:
        return f"user:{current_user.id}"

    user_agent = request.headers.get('User-Agent', '')[:50]
    identifier = f"ip:{get_remote_address()}:{hash(user_agent) % 10000}"
    return identifier


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)


    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bcrypt.init_app(app)
    moment.init_app(app)
    limiter.init_app(app)

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
        """自定义速率限制错误页面"""
        from flask import request
        import random
        from app.routes.utils import log_security_event

        # 记录安全事件（限制频率）
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

    # 自动创建管理员账号（如果不存在）
    with app.app_context():
        db.create_all()

        from app.models import User, Role

        # 检查是否需要创建管理员
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@blog.com',
                is_admin=True
            )
            admin_user.set_password('admin')
            db.session.add(admin_user)

            # 创建默认角色
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin')
                db.session.add(admin_role)

            user_role = Role.query.filter_by(name='user').first()
            if not user_role:
                user_role = Role(name='user')
                db.session.add(user_role)

            db.session.commit()
            print("已自动创建管理员账号: admin / admin")

        # 确保有默认分类
        from app.models import Category
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
            print("已自动创建默认分类")

    # 创建管理员账号的命令行命令
    @app.cli.command("create-admin")
    def create_admin_command():
        """创建管理员账号命令"""
        from app.models import User

        username = input("请输入管理员用户名 [admin]: ") or "admin"
        email = input("请输入管理员邮箱 [admin@blog.com]: ") or "admin@blog.com"
        password = input("请输入管理员密码: ")

        if not password:
            print("错误：密码不能为空！")
            return

        # 检查用户是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            # 提升现有用户为管理员
            existing_user.is_admin = True
            existing_user.email = email
            existing_user.set_password(password)
            db.session.commit()
            print(f"已将用户 {username} 提升为管理员")
        else:
            # 创建新管理员
            admin_user = User(username=username, email=email, is_admin=True)
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"已创建管理员账号: {username}")

        print("管理员账号创建完成！")

    @app.cli.command("list-admins")
    def list_admins_command():
        """列出所有管理员"""
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
        """创建样本数据"""
        import random
        from datetime import datetime, timedelta
        from app.models import User, Post, Comment, Category, Tag, Role

        print("开始创建样本数据...")

        # 创建普通用户（如果不存在）
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
                print(f"创建用户: {user.username}")

        db.session.commit()

        # 创建样本文章
        users = User.query.all()
        categories = Category.query.all()

        if users and categories:
            posts_content = [
                {
                    'title': 'Flask Web开发入门指南',
                    'content': 'Flask是一个轻量级的Python Web框架，它简单易用，非常适合初学者和快速开发。',
                    'category': categories[0]  # 第一个分类
                },
                {
                    'title': 'Python数据库操作详解',
                    'content': '在Python中，我们可以使用多种方式连接数据库，最常用的是SQLAlchemy。',
                    'category': categories[0]
                },
                {
                    'title': '我的编程学习之路',
                    'content': '还记得第一次接触编程是在大学时期，那时候对代码充满了好奇和敬畏。',
                    'category': categories[1]  # 第二个分类
                }
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
                print(f"创建文章: {post.title}")

            db.session.commit()
            print("样本数据创建完成！")
        else:
            print("无法创建样本数据：缺少用户或分类")

    # Shell上下文处理器
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Post, Comment, Category, Tag, Role, LogEntry
        return {
            'db': db,
            'User': User,
            'Post': Post,
            'Comment': Comment,
            'Category': Category,
            'Tag': Tag,
            'Role': Role,
            'LogEntry': LogEntry
        }

    return app