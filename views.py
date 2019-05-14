import datetime
import json
from collections import defaultdict
from decimal import Decimal

import redis
import telegram
from dateutil.relativedelta import relativedelta
from flask import current_app
from sqlalchemy import extract
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup)
from telegram.ext import (CallbackQueryHandler, CommandHandler, Dispatcher,
                          Filters, MessageHandler)

from config import BOT_TOKEN, IN_KEYWORD, KEYBOARD
from models import Bill, User, db

bot = telegram.Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None)
keyboard = ReplyKeyboardMarkup(KEYBOARD)

Redis = redis.StrictRedis(decode_responses=True)

# TODO /year 每月消费对比

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
            reply = f'支出：{amount}元，类目：{bill["category"]}'
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
        update.message.reply_text('welcome message', reply_markup=keyboard)
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

def month_command_handler(bot, update):

    # TODO 指定月份查询
    # TODO 查看账单详情
    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    dt_now = datetime.datetime.utcnow()
    callback_data = {
        'msg_type': 'month',
        'month': dt_now.strftime('%Y-%m'),
        'button': 'previous'
    }
    inline_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('<', callback_data=json.dumps(callback_data))
    ]])
    update.message.reply_text(get_month_statistic(user, dt_now.year, dt_now.month), reply_markup=inline_keyboard)

def callback_query_handler(bot, update):

    data = json.loads(update.callback_query.data)
    user = User.query.filter_by(username=update.callback_query.from_user.username).first()
    dt_now = datetime.datetime.utcnow()

    if data['msg_type'] == 'month':

        dt = datetime.datetime.strptime(data['month'], '%Y-%m')
        dt += relativedelta(months= 1 if data['button'] == 'next' else -1)

        statistic = get_month_statistic(user, dt.year, dt.month)
        callback_data = {
            'msg_type': 'month',
            'month': dt.strftime('%Y-%m')
        }
        if dt.year == dt_now.year and dt.month == dt_now.month:
            inline_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'}))
            ]])
        else:
            inline_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'})),
                InlineKeyboardButton('>', callback_data=json.dumps({**callback_data, 'button': 'next'}))
            ]])

        update.callback_query.edit_message_text(statistic, reply_markup=inline_keyboard)

    update.callback_query.answer()

def get_month_statistic(user:User, year:int, month:int)->str:

    bills = user.bills.filter(db.and_(
        extract('year', Bill.create_time) == year,
        extract('month', Bill.create_time) == month
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
    bills_out = sorted(bills_out.items(), key=lambda item:item[1], reverse=True)

    begin_part = f'{year}年{month}月收支统计\n\n'
    tabs = '\t\t\t\t\t\t\t'
    in_part = f'收入：{str(sum_in)}元\n'
    out_part = f'支出：{str(sum_out)}元\n\n'
    if not bills_out:
        out_part += f'{tabs}-  无\n\n'
    else:
        for category, amount in bills_out:
            out_part += f'{tabs}-  {category}: {str(amount)}元\n'
        out_part += '\n'
    return (begin_part + out_part + in_part).rstrip()

def error_handler(bot, update, error):
    current_app.logger.error(error)
    update.message.reply_text('Something wrong')


dispatcher.add_handler(CallbackQueryHandler(callback_query_handler))
dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))
dispatcher.add_handler(CommandHandler('start', start_handler))
dispatcher.add_handler(CommandHandler('set_balance', set_balance_handler))
dispatcher.add_handler(CommandHandler('balance', get_balance))
dispatcher.add_handler(CommandHandler('month', month_command_handler))
dispatcher.add_handler(CommandHandler('cancel', cancel_handler))
dispatcher.add_error_handler(error_handler)
