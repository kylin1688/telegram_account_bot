from flask_sqlalchemy import SQLAlchemy
import datetime
from datetime import timezone, timedelta
from config import TIMEZONE_HOURS

db = SQLAlchemy()


def get_datetime():
    utc_dt = datetime.datetime.utcnow()
    return utc_dt.astimezone(timezone(timedelta(hours=TIMEZONE_HOURS)))


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    first_name = db.Column(db.String(100))
    balance = db.Column(db.Numeric(10, 2), default=0)
    chat_id = db.Column(db.Integer)
    planned_month_deposit = db.Column(db.Numeric(10, 2), default=None)


class Bill(db.Model):
    __tablename__ = 'bill'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_time = db.Column(db.DateTime, default=datetime.datetime.now)
    type = db.Column(db.String(20), default='out')
    amount = db.Column(db.Numeric(10, 2))
    category = db.Column(db.String(100))
    name = db.Column(db.String(100), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('bills', lazy='dynamic'))

    def __repr__(self):
        return '{:12} '.format(str(self.amount) + '元') \
               + '{:4} '.format(self.category) \
               + ((" " + self.name) if self.name else "")
