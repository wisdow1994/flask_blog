from app import create_app, db
from app.models import User, Role, Post

from flask_script import Server, Manager
from flask_migrate import Migrate, MigrateCommand

app = create_app('default')
manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)
manager.add_command('server', Server)


@manager.shell
def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Post=Post)


if __name__ == '__main__':
    manager.run()
