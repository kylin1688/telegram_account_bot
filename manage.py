import os
from dotenv import load_dotenv

# 需要先加载.env的参数，否则导入config模块的时候会读不到环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell

from app import create_app, db

app = create_app(os.environ.get("FLASK_CONFIG") or "production")
manager = Manager(app)

migrate = Migrate(app, db)


def make_shell_context():
    return {"app": app, "db": db}


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)

if __name__ == "__main__":
    manager.run()
