from flask import Flask, request, current_app
import telegram
from views import dispatcher, bot
from models import db
from flask_script import Manager, Shell, Server
from flask_migrate import Migrate, MigrateCommand
from config import AppConfig

app  = Flask(__name__)
app.config.from_object(AppConfig)
db.init_app(app)

@app.route('/hook', methods=['POST'])
def webhook_handler():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    try:
        dispatcher.process_update(update)
    except:
        current_app.logger.exception('Something wrong.')
    return 'ok'

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command('shell', Shell(make_context=lambda:{'app': app, 'db': db}))
manager.add_command('db', MigrateCommand)
manager.add_command('runserver', Server(host=app.config['HOST'], port=app.config['PORT']))

if __name__ == "__main__":
    manager.run()