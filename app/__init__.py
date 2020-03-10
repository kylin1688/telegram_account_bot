import logging

from flask import Flask
from flask.logging import default_handler

from app.models import db
from app.utils.hooks import log_request_params, log_response
from app.webhook import telegram_bp
from app.utils import multilog
from app.utils.error import handle_exception
from config import config_map


def create_app(config_name: str):
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    @app.route('/', endpoint='ping_pong')
    def ping_pong():
        return "I'm still alive.\n", 200

    db.init_app(app)

    register_logger(app)
    register_hooks(app)
    register_blueprints(app)
    register_error_handlers(app)

    return app


def register_blueprints(app: Flask):
    app.register_blueprint(telegram_bp, url_prefix='/telegram')


def register_error_handlers(app: Flask):
    app.register_error_handler(Exception, handle_exception)


def register_hooks(app: Flask):
    app.before_request(log_request_params)
    app.after_request(log_response)


def register_logger(app: Flask):
    # 写入日志文件
    app.logger.removeHandler(default_handler)
    handler = multilog.MyLoggerHandler('flask', encoding='UTF-8', when='H')
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s - %(lineno)s - %(message)s'
    )
    handler.setFormatter(logging_format)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    # 写入控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    app.logger.addHandler(ch)
    app.logger.setLevel(logging.DEBUG)
