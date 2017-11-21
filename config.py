import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.urandom(24)
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.163.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = '18873614432@163.com'
    MAIL_PASSWORD = '123456789ef'
    # 这里的邮箱为你的163邮箱，密码为你在163邮箱里面的
    # （设置 -> POP3/SMTP/IMAP -> 客户端授权密码） 里面设置的
    # 而不是实际你登录163邮箱的密码
    # 国内邮箱协议用SSL协议而不是TLS协议（我测试的是TLS协议不成功）
    FLASKY_MAIL_SUBJECT_PREFIX = '[blog]'
    FLASKY_MAIL_SENDER = '管理员 <18873614432@163.com>'
    FLASKY_ADMIN = '1102941512@qq.com'

    FLASKY_POSTS_PER_PAGE = 10  # 不设置的话是一页20篇,但是虚拟生存的文章太少

    @staticmethod
    def init_app(app):  # 给配置文件的基类预留一个接口,在工厂函数中也使用,新加的内容直接写在配置中
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.db')

    FLASKY_FOLLOWERS_PER_PAGE = 20
    FLASKY_COMMENTS_PER_PAGE = 10


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.db')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-pro.db')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
