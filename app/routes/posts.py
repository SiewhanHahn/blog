from flask import Blueprint, render_template, flash, redirect, url_for, request, abort, current_app
from flask_login import current_user, login_required
from app import db
from app.forms import PostForm, CommentForm
from app.models import Post, Comment, Tag, Category
from app.routes.utils import log_security_event  # 导入公共函数

bp = Blueprint('posts', __name__)


@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()

    # 检查是否有分类可用
    categories = Category.query.all()
    if not categories:
        flash('请先创建分类再发布文章。', 'warning')
        return redirect(url_for('main.index'))

    if form.validate_on_submit():
        # 验证分类是否存在
        category = Category.query.get(form.category.data)
        if not category:
            flash('选择的分类不存在。', 'danger')
            return render_template('create_post.html', title='发布新文章', form=form)

        # Handle tags
        tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
        tags = []
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, slug=tag_name.lower().replace(' ', '-'))
                db.session.add(tag)
                # 移除这里的 db.session.commit()
            tags.append(tag)

        post = Post(
            title=form.title.data,
            content=form.content.data,
            user_id=current_user.id,
            category_id=form.category.data,
            tags=tags
        )
        db.session.add(post)
        db.session.commit()
        flash('您的文章已发布！', 'success')
        log_security_event(f"User {current_user.username} created post: {post.title}", user_id=current_user.id)
        return redirect(url_for('main.index'))

    return render_template('create_post.html', title='发布新文章', form=form)


@bp.route('/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    """显示单个文章和评论"""
    post = Post.query.get_or_404(post_id)
    form = CommentForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('请先登录后发表评论。', 'warning')
            return redirect(url_for('auth.login'))

        comment = Comment(
            content=form.content.data,
            user_id=current_user.id,
            post_id=post_id
        )
        db.session.add(comment)
        db.session.commit()
        flash('评论已发布！', 'success')
        return redirect(url_for('posts.post', post_id=post_id))

    comments = post.comments.order_by(Comment.created_at.asc()).all()
    return render_template('post.html', post=post, form=form, comments=comments)


@bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """编辑文章"""
    post = Post.query.get_or_404(post_id)

    # 检查权限：只有作者或管理员可以编辑
    if post.author != current_user and not current_user.is_admin:
        flash('您没有权限编辑此文章。', 'danger')
        return redirect(url_for('posts.post', post_id=post_id))

    form = PostForm()

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.category_id = form.category.data

        # 处理标签更新
        tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
        tags = []
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, slug=tag_name.lower().replace(' ', '-'))
                db.session.add(tag)
                # 移除这里的 db.session.commit()
            tags.append(tag)
        post.tags = tags

        db.session.commit()
        flash('文章已更新！', 'success')
        return redirect(url_for('posts.post', post_id=post_id))

    # 预填充表单数据
    form.title.data = post.title
    form.content.data = post.content
    form.category.data = post.category_id
    form.tags.data = ', '.join([tag.name for tag in post.tags])

    return render_template('edit_post.html', form=form, post_id=post_id)


@bp.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    """删除文章"""
    post = Post.query.get_or_404(post_id)

    # 检查权限：只有作者或管理员可以删除
    if post.author != current_user and not current_user.is_admin:
        flash('您没有权限删除此文章。', 'danger')
        return redirect(url_for('posts.post', post_id=post_id))

    db.session.delete(post)
    db.session.commit()
    flash('文章已删除。', 'success')
    return redirect(url_for('main.index'))  # 修复：移除 'main. Index' 中的空格