from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError

from ..models import User


class LoginForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('一个月免登陆')
    submit = SubmitField('登陆')


class RegisterForm(FlaskForm):
    email = StringField('电子邮箱', validators=[DataRequired(), Length(1, 64), Email()])

    username = StringField('用户昵称', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', flags=0, message='用户名只能包含大小写字母,数字,小数点,下划线!')])

    password = PasswordField('密码', validators=[
        DataRequired(), EqualTo('password2', message='两次输入的密码不一致!')])

    password2 = PasswordField('确认密码', validators=[DataRequired()])

    submit = SubmitField('注册')

    def validate_email(self, field):  # validate_开头的函数和常规验证函数一样被调用
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('此邮箱已被注册!')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('此昵称已被人使用!')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('旧密码', validators=[DataRequired()])

    password = PasswordField('新密码', validators=[
        DataRequired(), EqualTo('password2', message='两次输入的密码不一致!')])
    password2 = PasswordField('确认新密码', validators=[DataRequired()])
    submit = SubmitField('修改密码')


class PasswordResetForm(FlaskForm):
    email = StringField('注册账户所用的邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('新密码', validators=[
        DataRequired(), EqualTo('password2', message='两次输入的密码不一致')])
    password2 = PasswordField('确认密码', validators=[DataRequired()])
    submit = SubmitField('重置密码')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('你填错地址了!')


class PasswordResetRequestForm(FlaskForm):
    email = StringField('此账户的邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('重置密码')


class ChangeEmailForm(FlaskForm):
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('更换邮箱')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已经被人使用.')
