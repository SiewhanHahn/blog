from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from app import db
from app.models import Category
from app.forms import CategoryForm  # 需要创建这个表单

bp = Blueprint('categories', __name__)


@bp.route('/categories')
def list_categories():
    categories = Category.query.all()
    return render_template('categories.html', title='分类列表', categories=categories)


@bp.route('/create_category', methods=['GET', 'POST'])
@login_required
def create_category():
    if not current_user.is_admin:
        flash('您没有权限创建分类。', 'danger')
        return redirect(url_for('main.index'))

    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, slug=form.slug.data)
        db.session.add(category)
        db.session.commit()
        flash('分类创建成功！', 'success')
        return redirect(url_for('categories.list_categories'))

    return render_template('create_category.html', title='创建分类', form=form)