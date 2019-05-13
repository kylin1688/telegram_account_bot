import telegram
from collections import defaultdict
from telegram import ReplyKeyboardMarkup
from telegram.ext import Dispatcher, Filters, CommandHandler, MessageHandler
from models import db, User, Bill
from decimal import Decimal
import redis
import json
from flask import current_app
from sqlalchemy import extract
import datetime
from config import BOT_TOKEN, KEYBOARD, IN_KEYWORD

bot = telegram.Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None)
keyboard = ReplyKeyboardMarkup(KEYBOARD)

Redis = redis.StrictRedis(decode_responses=True)

def reply_handler(bot, update):

    tg_user = update.message.from_user
    text = update.message.text
    raw = Redis.get(tg_user.username)

    if raw is None:
        Redis.set(tg_user.username, json.dumps({'category': text, 'type': 'out' if text != IN_KEYWORD else 'in'}))
        update.message.reply_text('请输入金额')

    else:

        bill = json.loads(raw)
        user = User.query.filter_by(username=tg_user.username).first()

        splited_text = text.split(' ')
        if len(splited_text) == 2:
            amount, name = splited_text
            bill.update({'amount': Decimal(amount), 'name': name, 'user_id': user.id})
        else:
            amount = text
            bill.update({'amount': Decimal(amount), 'user_id': user.id})
        
        if bill['type'] == 'out':
            reply = f'支出：{amount}元，类目：{bill["type"]}'
            user.balance -= Decimal(amount)
        elif bill['type'] == 'in':
            reply = f'收入：{amount}元' + f'{bill["name"]}' if bill.get('name') else ''
            user.balance += Decimal(amount)

        db.session.add(Bill(**bill))
        db.session.commit()
        Redis.delete(tg_user.username)

        update.message.reply_text(reply + f'\n当前余额：{str(user.balance)}元')

def start_handler(bot, update):
    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    if user is None:
        db.session.add(User(username=tg_user.username, first_name=tg_user.first_name))
        db.session.commit()
        update.message.reply_text('welcome message', 
            reply_markup=keyboard)
    else:
        update.message.reply_text('welcome back', reply_markup=keyboard)

def get_balance(bot, update):
    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    if user is not None:
        update.message.reply_text(f'当前余额：{user.balance}元')

def cancel_handler(bot, update):
    tg_user = update.message.from_user
    Redis.delete(tg_user.username)
    update.message.reply_text(f'OK')

def set_balance_handler(bot, update):

    tg_user = update.message.from_user
    balance = update.message.text.replace('/set_balance ', '')
    user = User.query.filter_by(username=tg_user.username).first()
    if user is not None:
        user.balance = Decimal(balance)
        db.session.commit()
    update.message.reply_text(f'余额设置成功，当前余额：{balance}元')

def month_statistic(bot, update):

    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    dt_now = datetime.datetime.utcnow()

    bills = user.bills.filter(db.and_(
        extract('year', Bill.create_time) == dt_now.year,
        extract('month', Bill.create_time) == dt_now.month
    )).all()

    bills_in = defaultdict(lambda :Decimal('0'))
    bills_out = defaultdict(lambda :Decimal('0'))
    sum_out = sum_in = Decimal('0')
    for bill in bills:
        if bill.type == 'in':
            bills_in[bill.category] += bill.amount
            sum_in += bill.amount
        elif bill.type == 'out':
            sum_out += bill.amount
            bills_out[bill.category] += bill.amount

    begin_part = f'{dt_now.year}年{dt_now.month}月收支统计\n\n'
    def template(title, bills, tabs='\t\t\t\t\t\t\t'):
        content = f'{title}\n\n'
        if not bills:
            content += f'{tabs}-  无\n'
        else:
            for k, v in bills.items():
                content += f'{tabs}-  {k}: {str(v)}元\n'
        content += '\n'
        return content
    out_part = template(f'支出：{str(sum_out)}元', bills_out)
    in_part = f'收入：{str(sum_in)}元\n'

    update.message.reply_text((begin_part + out_part + in_part).rstrip())

def error_handler(bot, update, error):
    current_app.logger.error(error)
    update.message.reply_text('Something wrong')

dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))
dispatcher.add_handler(CommandHandler('start', start_handler))
dispatcher.add_handler(CommandHandler('set_balance', set_balance_handler))
dispatcher.add_handler(CommandHandler('balance', get_balance))
dispatcher.add_handler(CommandHandler('month', month_statistic))
dispatcher.add_handler(CommandHandler('cancel', cancel_handler))
dispatcher.add_error_handler(error_handler)
