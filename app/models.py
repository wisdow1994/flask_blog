from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime
import hashlib
from markdown import markdown
import bleach
from flask import current_app, request
from app import db, login_manage


class Permission:  # 权限常量,由自己定义和设计
    FOLLOW = 0X01
    COMMENT = 0X02
    WRITE_ARTICLES = 0X04
    MODERATE_COMMENTS = 0X08
    ADMINISTER = 0X80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    default = db.Column(db.Boolean, default=False, index=True)
    # 普通用户角色的default字段要设为True ，其他都设为False，用户注册时，其角色会被设为默认角色。
    permissions = db.Column(db.Integer)

    users = db.relationship('User', backref='role', lazy='dynamic')  # 角色与用户的一对多

    @staticmethod
    def insert_roles():
        roles = {
            '用户': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),  # 值是一个元组,默认创建的是这一个角色组合
            '内容协管员': (Permission.FOLLOW |
                         Permission.COMMENT |
                         Permission.WRITE_ARTICLES |
                         Permission.MODERATE_COMMENTS, False),
            '管理员': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            # 等价于 role.permissions, role.default = roles[r]
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()
        # insert_roles() 函数并不直接创建新角色对象，而是通过角色名查找现有的角色，然后再进行更新。
        # 只有当数据库中没有某个角色名时才会创建新角色对象。
        # 如果以后更新了角色列表，就可以执行更新操作了。要想添加新角色，或者修改角色的权限，
        # 修改roles 数组，再运行函数即可

    def __repr__(self):
        return f'<Role角色名:{self.name}>'


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))  # 使用role表的外键

    password_hash = db.Column(db.String(128))  # 注册账户,由密码生成hash值

    confirmed = db.Column(db.Boolean, default=False)  # 账户激活的状态,布尔值默认为False

    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text)
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    avatar_hash = db.Column(db.String(64))  # 头像hash

    posts = db.relationship('Post', backref='author', lazy='dynamic')  # 作者与文章的一对多

    comments = db.relationship('Comment', backref='author', lazy='dynamic')  # 作者与评论的一对多

    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def is_following(self, user):  # 是否关注了这个用户
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def id_followed_by(self, user):  # 是否为我的粉丝
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def follow(self, user):  # 关注用户
        if not self.is_following(user):  # 还没有关注这个用户
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):  # 取消关注
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    @property
    def followed_posts(self):  # 属性函数,返回用户所有关注用户的文章
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)

    def ping(self):  # 更新最后访问时间
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:  # 先给管理员权限
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:  # 默认用户权限为default=True的权限组合
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:  # 如果用存在的这个用户没有头像hash
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        self.followed.append(Follow(followed=self))  # 用户自己关注自己,等价于self.follow(self)

    @staticmethod
    def add_self_follows():  # 用户自己关注自己,对于已经部署的应用,采取静态方法更新
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    @property
    def password(self):
        raise AttributeError('密码是不可读的！！！')

    @password.setter
    def password(self, password):  # 生成password_hash值,
        # 这个函数名是单独存在的,属性函数property设置的password
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):  # 验证密码的正确性
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):  # 生成确认账户状态的安全令牌
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):  # 账户确认,令牌符合时,更新当前用户的confirmed布尔值为True
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            # 除了检验令牌,检查令牌中的 id 是否和存储在current_user 中的已登录用户匹配
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):  # 重置密码时使用的安全令牌
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):  # 生成用于修改邮箱时使用的令牌
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):  # 验证令牌
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()  # 邮箱修改后,hash也需要重新计算
        db.session.add(self)
        return True

    def can(self, permissions):  # 对用户的权限进行验证
        return self.role is not None and (self.role.permissions & permissions) == permissions
        # 权限位与操作 (0x07&0x05)==0x05 True

    def is_administrator(self):  # 管理员权限验证
        return self.can(Permission.ADMINISTER)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    @staticmethod
    def generate_fake(count=100):  # 生成虚拟数据,先不用管它的写法
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __repr__(self):
        return self.username
        # return f'<User用户名: {self.username}>'


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.Text)  # 存储用户提交的markdown源文本

    body_html = db.Column(db.Text)  # 存储经过后台处理过的html格式内容

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 注意,删除数据库的时候,要把这个单词改过来

    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def generate_fake(count=100):  # 生成虚拟数据,先不用管它的写法
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    def __repr__(self):
        return f'Post的author_id: {self.author_id}'

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


db.event.listen(Post.body, 'set', Post.on_changed_body)  # 监听body的修改和新设,自动调用函数


class AnonymousUser(AnonymousUserMixin):  # 出于一致性,不用检测用户是否登陆,对游客也可以权限检测方法
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manage.anonymous_user = AnonymousUser


@login_manage.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
