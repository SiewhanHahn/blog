from flask import Blueprint, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from app import db
from app.models import Comment
from app.routes.utils import log_security_event  # 导入公共函数

bp = Blueprint('comments', __name__)


@bp.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    # Check if current user is the author of the comment, an admin, or the author of the post
    if comment.author != current_user and not current_user.is_admin and comment.post.author != current_user:
        flash('您没有权限删除此评论。', 'danger')
        abort(403)

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash('评论已删除。', 'success')
    log_security_event(f"User {current_user.username} deleted comment (ID: {comment_id})", user_id=current_user.id)
    return redirect(url_for('posts.post', post_id=post_id))