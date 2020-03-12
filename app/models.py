import datetime
import json

from flask_restplus import fields
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import sqltypes

db = SQLAlchemy()


class Marshaling:
    # 用来给sqlalchemy模型自动生成序列化规则，供flask-restplus使用
    # 偷懒用的，不放心还是可以直接手写模型，没有影响

    type_mapper = {
        sqltypes.String: fields.String,
        sqltypes.Integer: fields.Integer,
        sqltypes.Numeric: fields.Float,
    }

    @classmethod
    def auto_marshaling_model(cls):
        model: dict = {}
        for column in cls.__table__.c:
            pass
        return {
            column.name: cls.type_mapper[type(column.type)] for column in cls.__table__.c
        }


class User(db.Model, Marshaling):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    first_name = db.Column(db.String(100))
    balance = db.Column(db.Numeric(10, 2), default=0)
    chat_id = db.Column(db.Integer)
    planned_month_deposit = db.Column(db.Numeric(10, 2), default=None)

    @classmethod
    def auto_marshaling_model(cls):
        model: dict = super().auto_marshaling_model()
        model['id'] = fields.Integer(readonly=True)
        return model


class Bill(db.Model, Marshaling):
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


class ScheduledBillTask(db.Model, Marshaling):
    __tablename__ = 'task'

    id = db.Column(db.String(50), primary_key=True)
    amount = db.Column(db.Numeric(10, 2))
    trigger = db.Column(db.String(10))
    category = db.Column(db.String(100))
    type = db.Column(db.String(20))
    name = db.Column(db.String(100), nullable=True)
    trigger_kwargs = db.Column(db.String(200))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('tasks', lazy='dynamic'))

    @classmethod
    def auto_marshaling_model(cls):
        model: dict = super().auto_marshaling_model()

        class TriggerKwargs(fields.Raw):
            def format(self, value):
                return json.loads(value)

        model['trigger_kwargs'] = TriggerKwargs(required=True)
        model['id'] = fields.String(readonly=True)
        return model
