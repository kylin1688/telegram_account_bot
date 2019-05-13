from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    first_name = db.Column(db.String(100))
    balance = db.Column(db.Numeric(10, 2), default=0)

class Bill(db.Model):
    __tablename__ = 'bill'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    type = db.Column(db.String(20), default='out')
    amount = db.Column(db.Numeric(10, 2))
    category = db.Column(db.String(100))
    name = db.Column(db.String(100), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('bills', lazy='dynamic'))

    def __repr__(self):
        return f''