from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, Email, Regexp, ValidationError
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField
from flask_pagedown.fields import PageDownField
from ..models import Role, User


class CommentFoem(FlaskForm):
    body = StringField('发表你的评论!', validators=[DataRequired()])
    submit = SubmitField('提交')


class NameForm(FlaskForm):
    name = StringField('你的名字是?', validators=[DataRequired()])
    submit = SubmitField('提交')


class PostForm(FlaskForm):
    body = PageDownField('你想说些什么?', validators=[DataRequired()])
    submit = SubmitField('发布')


class EditProfileForm(FlaskForm):
    name = StringField('真实姓名', default='未填写', validators=[Length(0, 64)])
    location = StringField('所在城市', default='未填写', validators=[Length(0, 64)])
    about_me = TextAreaField('关于我', default='未填写', validators=[Length(0, 64)])

    submit = SubmitField('修改')


class EditProfileAdminForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])

    username = StringField('用户昵称', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', flags=0, message='用户名只能包含大小写字母,数字,小数点,下划线!')])

    confirmed = BooleanField('账户确认状态')
    role = SelectField('权限', coerce=int)

    name = StringField('真实姓名', default='未填写', validators=[Length(0, 64)])
    location = StringField('所在城市', default='未填写', validators=[Length(0, 64)])
    about_me = TextAreaField('关于我', default='未填写', validators=[Length(0, 64)])

    submit = SubmitField('修改')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        # 下拉菜单的元素由元组组成,第一个数字是存储的role.id,第二个是菜单显示的文本
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):  # validate_开头的函数和常规验证函数一样被调用
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('此邮箱已被注册!')

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('此昵称已被人使用!')
