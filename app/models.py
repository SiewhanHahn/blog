from datetime import datetime, timezone
from app import db, login, bcrypt
from flask_login import UserMixin
from markdown import markdown
import bleach

# Many-to-Many relationship between Post and Tag
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Many-to-Many relationship between User and Role
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    # 一对多，用户->文章
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # 一对多，用户->评论
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    # 多对多，用户<->角色
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                            backref=db.backref('users', lazy=True))
    # 一对多，用户->日志记录
    log_entries = db.relationship('LogEntry', backref='user', lazy='dynamic')

    # 安全方法
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)

    posts = db.relationship('Post', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    # slug：URL友好的标识符
    slug = db.Column(db.String(64), unique=True, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)  # 可存储原始 Markdown 内容
    content_html = db.Column(db.Text)  # 转换后的安全HTML
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    # 级联删除，删除文章时自动删除评论
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary=post_tags, lazy='subquery',
                            backref=db.backref('posts', lazy=True))

    def __repr__(self):
        return f'<Post {self.title}>'

    @property
    def comments_count(self):
        """返回文章的评论数量"""
        return self.comments.count()

    # XSS防护机制
    @staticmethod
    def on_changed_content(target, value, oldvalue, initiator):
        # HTMl使用标签白名单
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img']
        allowed_attrs = {'*': ['class'], 'a': ['href', 'rel'], 'img': ['src', 'alt']}
        # 用户输入的Markdown转换为HTML
        # 安全处理链接，防止恶意跳转
        # 移除所有不在白名单中的 HTML 标签和属性
        # 在清理后的 HTML 中安全地识别和转换链接
        target.content_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=allowed_attrs, strip=True))


db.event.listen(Post.content, 'set', Post.on_changed_content)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text) # Stored sanitized HTML
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} by {self.user_id}>'

    # XSS 防护
    @staticmethod
    def on_changed_content(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'b', 'blockquote', 'code', 'em', 'i', 'strong']
        allowed_attrs = {'a': ['href', 'rel']}
        target.content_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=allowed_attrs, strip=True))

db.event.listen(Comment.content, 'set', Comment.on_changed_content)


class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Nullable for unauthenticated users
    action = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<LogEntry {self.action} from {self.ip_address} at {self.timestamp}>'


@login.user_loader
def load_user(id):
    return User.query.get(int(id))