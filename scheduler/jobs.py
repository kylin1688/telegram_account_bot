import datetime
import json
import os
from decimal import Decimal
from typing import List

from app.models import db, User, Bill
from app import create_app
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

from app.webhook.handlers import get_day_details

app = create_app(os.environ.get('FLASK_CONFIG') or 'development')
bot: Bot = Bot(os.environ.get('BOT_TOKEN'))


def create_new_bill(user_id, amount: str, category: str, type: str, name: str = None):
    with app.app_context():
        user: User = User.query.filter_by(id=user_id).first()
        # new bill
        bill: Bill = Bill(user_id=user_id, type=type, amount=Decimal(amount), category=category, name=name)
        db.session.add(bill)
        # update user balance
        if type == 'out':
            reply = f'支出：{amount}元，类别：{category}'
            user.balance -= Decimal(amount)
        else:
            reply = f'收入：{amount}元' + f'{name}' if name else ''
            user.balance += Decimal(amount)
        db.session.commit()
        # send message
        callback_data = {
            'msg_type': 'periodic',
            'bill_id': bill.id,
        }
        inline_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('撤销', callback_data=json.dumps(callback_data))]])
        bot.send_message(user.chat_id, f'{reply}\n当前余额：{str(user.balance)}元',
                         reply_markup=inline_keyboard, disable_notification=True)


def send_daily_bills():
    with app.app_context():
        users: List[User] = User.query.all()
        dt_now = datetime.datetime.now()
        for user in users:
            details: str = get_day_details(user, dt_now.year, dt_now.month, dt_now.day)
            bot.send_message(user.chat_id, details)
