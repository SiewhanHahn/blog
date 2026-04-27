from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user
from app import db, limiter
from app.models import User, Post, Category, Tag
from app.routes.utils import log_security_event # 导入公共函数

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
@limiter.limit("30 per minute") # Rate limiting for index page
def index():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=current_app.config.get('POSTS_PER_PAGE', 10), error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='首页', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)

@bp.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

@bp.route('/category/<slug>')
def category_posts(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    posts = category.posts.order_by(Post.created_at.desc()).all()
    return render_template('category_posts.html', title=category.name, category=category, posts=posts)

@bp.route('/tag/<slug>')
def tag_posts(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    posts = tag.posts.order_by(Post.created_at.desc()).all()
    return render_template('tag_posts.html', title=tag.name, tag=tag, posts=posts)