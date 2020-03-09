import datetime
import json
from collections import defaultdict
from decimal import Decimal

import redis
from dateutil.relativedelta import relativedelta
from flask import current_app
from sqlalchemy import extract, text
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup)

from config import IN_KEYWORD, KEYBOARD
from app.models import Bill, User, db, get_datetime

keyboard = ReplyKeyboardMarkup(KEYBOARD)

Redis = redis.StrictRedis(decode_responses=True)


# TODO /day 重新添加遗漏账单
# TODO /year 每月消费对比

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


def deposit_command_handler(bot, update):
    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    deposit = update.message.text.replace('/deposit ', '')
    if user is not None:
        user.planned_month_deposit = Decimal(deposit)
        db.session.commit()
        update.message.reply_text(f'月计划存款已变更，当前数额：{deposit}元')


def reply_handler(bot, update):
    tg_user = update.message.from_user
    text = update.message.text
    raw = Redis.get(tg_user.username)

    if raw is None:
        Redis.set(tg_user.username, json.dumps({'category': text, 'type': 'out' if text != IN_KEYWORD else 'in'}))
        update.message.reply_text(f'账单类别：{text}，请输入账单金额\n若想取消本次操作，请输入 /cancel')

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
            reply = f'支出：{amount}元，类别：{bill["category"]}'
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
        db.session.add(User(username=tg_user.username, first_name=tg_user.first_name,
                            chat_id=update.message.chat.id))
        db.session.commit()
        update.message.reply_text('welcome message', reply_markup=keyboard)
    else:
        update.message.reply_text('welcome back', reply_markup=keyboard)


def day_command_handler(bot, update):
    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    dt_now = get_datetime()
    details = get_day_details(user, dt_now.year, dt_now.month, dt_now.day)
    callback_data = {
        'msg_type': 'day',
        'day': dt_now.strftime('%Y-%m-%d')
    }
    inline_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'})),
        InlineKeyboardButton('>', callback_data=json.dumps({**callback_data, 'button': 'next'}))
    ]])
    update.message.reply_text(details, reply_markup=inline_keyboard)


def month_command_handler(bot, update):
    # TODO 指定月份查询

    tg_user = update.message.from_user
    user = User.query.filter_by(username=tg_user.username).first()
    dt_now = get_datetime()
    callback_data = {
        'msg_type': 'month',
        'month': dt_now.strftime('%Y-%m')
    }

    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'}))],
        [InlineKeyboardButton('详情', callback_data=json.dumps({**callback_data, 'button': 'details'}))]
    ])
    statistic = get_month_statistic(user, dt_now.year, dt_now.month)
    update.message.reply_text(statistic, reply_markup=inline_keyboard)


def callback_query_handler(bot, update):
    data = json.loads(update.callback_query.data)
    user = User.query.filter_by(username=update.callback_query.from_user.username).first()
    dt_now = get_datetime()

    if data['msg_type'] == 'month':

        dt = datetime.datetime.strptime(data['month'], '%Y-%m')
        if data['button'] in ('previous', 'next'):
            dt += relativedelta(months=1 if data['button'] == 'next' else -1)
            statistic = get_month_statistic(user, dt.year, dt.month)
            callback_data = {
                'msg_type': 'month',
                'month': dt.strftime('%Y-%m')
            }
            if dt.year == dt_now.year and dt.month == dt_now.month:
                inline_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'}))],
                    [InlineKeyboardButton('详情', callback_data=json.dumps({**callback_data, 'button': 'details'}))]
                ])
            else:
                inline_keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'})),
                    InlineKeyboardButton('>', callback_data=json.dumps({**callback_data, 'button': 'next'}))],
                    [InlineKeyboardButton('详情', callback_data=json.dumps({**callback_data, 'button': 'details'}))]])

            update.callback_query.edit_message_text(statistic, reply_markup=inline_keyboard)

        elif data['button'] == 'details':
            callback_data = {
                'msg_type': 'month_details',
                'month': data['month']
            }
            inline_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton('返回', callback_data=json.dumps(callback_data))
            ]])
            details = get_month_details(user, dt.year, dt.month)
            update.callback_query.edit_message_text(details, reply_markup=inline_keyboard)

    elif data['msg_type'] == 'month_details':

        dt = datetime.datetime.strptime(data['month'], '%Y-%m')
        statistic = get_month_statistic(user, dt.year, dt.month)
        callback_data = {
            'msg_type': 'month',
            'month': dt.strftime('%Y-%m')
        }
        if dt.year == dt_now.year and dt.month == dt_now.month:
            inline_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'}))],
                [InlineKeyboardButton('详情', callback_data=json.dumps({**callback_data, 'button': 'details'}))]
            ])
        else:
            inline_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'})),
                InlineKeyboardButton('>', callback_data=json.dumps({**callback_data, 'button': 'next'}))],
                [InlineKeyboardButton('详情', callback_data=json.dumps({**callback_data, 'button': 'details'}))]
            ])

        update.callback_query.edit_message_text(statistic, reply_markup=inline_keyboard)

    elif data['msg_type'] == 'day':

        dt = datetime.datetime.strptime(data['day'], '%Y-%m-%d')
        dt += relativedelta(days=1 if data['button'] == 'next' else -1)
        details = get_day_details(user, dt.year, dt.month, dt.day)

        callback_data = {
            'msg_type': 'day',
            'day': dt.strftime('%Y-%m-%d')
        }
        inline_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton('<', callback_data=json.dumps({**callback_data, 'button': 'previous'})),
            InlineKeyboardButton('>', callback_data=json.dumps({**callback_data, 'button': 'next'}))
        ]])
        update.callback_query.edit_message_text(details, reply_markup=inline_keyboard)

    elif data['msg_type'] == 'periodic':

        bill = Bill.query.get(data['bill_id'])
        db.session.delete(bill)
        if bill.type == 'out':
            user.balance += bill.amount
        elif bill.type == 'in':
            user.balance -= bill.amount
        db.session.commit()
        update.callback_query.edit_message_text(f'已撤销，当前余额：{str(user.balance)}元')

    update.callback_query.answer()


def get_month_statistic(user: User, year: int, month: int) -> str:
    bills = user.bills.filter(db.and_(
        extract('year', Bill.create_time) == year,
        extract('month', Bill.create_time) == month
    )).all()

    bills_in = defaultdict(lambda: Decimal('0'))
    bills_out = defaultdict(lambda: Decimal('0'))
    sum_out = sum_in = Decimal('0')
    for bill in bills:
        if bill.type == 'in':
            bills_in[bill.category] += bill.amount
            sum_in += bill.amount
        elif bill.type == 'out':
            sum_out += bill.amount
            bills_out[bill.category] += bill.amount
    bills_out = sorted(bills_out.items(), key=lambda item: item[1], reverse=True)

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

    result = begin_part + out_part + in_part
    if user.planned_month_deposit is not None:
        delta = sum_in - sum_out
        if delta > 0:
            left_budget = delta - user.planned_month_deposit
            result += f'\n净增：{str(delta)}元\n'
            result += f'剩余额度：{str(left_budget)}元\n'
    return result.rstrip()


def get_month_details(user: User, year: int, month: int) -> str:
    # 只展示支出的
    bills = user.bills.filter(db.and_(
        extract('year', Bill.create_time) == year,
        extract('month', Bill.create_time) == month
    ), Bill.type == 'out').order_by(text('-bill.amount')).all()

    bills_part = ''
    sum_out = Decimal('0')
    title = f'{year}年{month}月支出详情\n\n'
    for bill in bills:
        sum_out += bill.amount
        bills_part += f'{repr(bill)}\n'

    sum_part = f'合计消费：{str(sum_out)}元\n\n'
    return (title + sum_part + bills_part).rstrip()


def get_day_details(user: User, year: int, month: int, day: int) -> str:
    bills = user.bills.filter(db.and_(
        extract('year', Bill.create_time) == year,
        extract('month', Bill.create_time) == month,
        extract('day', Bill.create_time) == day
    ), Bill.type == 'out').order_by(text('bill.create_time')).all()

    bills_part = ''
    sum_out = Decimal('0')
    title = f'{month}月{day}日支出详情\n\n'
    for bill in bills:
        sum_out += bill.amount
        bills_part += f'{repr(bill)}\n'
    sum_part = f'合计消费：{str(sum_out)}元\n\n'
    return (title + sum_part + bills_part).rstrip()


def error_handler(bot, update, error):
    current_app.logger.error(error)
    update.message.reply_text('Something wrong')
