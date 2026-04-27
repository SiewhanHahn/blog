import os

# 配置类
class Config:

    # Flask加密密钥配置，会话加密，CSRF保护
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # 数据库配置，连接搭配本地数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'mysql+pymysql://root:root@localhost:3306/blog_db'

    # 禁用Flask-SQLAlchemy的事件追踪系统
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Admin 管理界面主题
    FLASK_ADMIN_SWATCH = 'cerulean'

    # Flask-limiter限流使用内存存储
    RATELIMIT_STORAGE_URI = "memory://"

    # 分页配置，每页显示10篇文章
    POSTS_PER_PAGE = 10