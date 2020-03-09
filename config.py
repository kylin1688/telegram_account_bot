import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    HOST = '0.0.0.0'
    PORT = '6000'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('PRO_DB_URL') or "sqlite:///" + os.path.join(basedir, "prod.sqlite")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'dev.sqlite')


TIMEZONE_HOURS = 8
IN_KEYWORD = '收入'
KEYBOARD = [
    ['出行', '饮食', '杂项'],
    ['娱乐', '购物'],
    [IN_KEYWORD]
]

config_map = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'default': DevelopmentConfig
}
