from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User, Category

# 登录表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

# 注册表单
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    password2 = PasswordField(
        '确认密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('该用户名已被使用，请选择其他用户名。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('该邮箱已被注册，请使用其他邮箱。')

# 发布文章
class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired()])
    content = TextAreaField('内容', validators=[DataRequired()])
    category = SelectField('分类', coerce=int, validators=[DataRequired()])
    tags = StringField('标签')
    submit = SubmitField('发布')

    # 动态初始化
    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        # 动态加载分类选项
        self.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
        # 如果没有分类，添加一个默认选项
        if not self.category.choices:
            self.category.choices = [(0, '请先创建分类')]

# 评论表单
class CommentForm(FlaskForm):
    content = TextAreaField('评论内容', validators=[DataRequired()])
    submit = SubmitField('提交评论')

# 搜索表单
class SearchForm(FlaskForm):
    q = StringField('搜索', validators=[DataRequired()])
    submit = SubmitField('搜索')

# 分类表单
class CategoryForm(FlaskForm):
    name = StringField('分类名称', validators=[DataRequired()])
    slug = StringField('URL标识', validators=[DataRequired()])
    submit = SubmitField('创建分类')