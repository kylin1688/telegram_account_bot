import telegram
from flask import Blueprint, request, current_app
from telegram import Update, Bot
from telegram.ext import Dispatcher, CallbackQueryHandler, MessageHandler, CommandHandler, Filters

from app.webhook.handlers import reply_handler, start_handler, day_command_handler, get_balance, cancel_handler, set_balance_handler, \
    deposit_command_handler, month_command_handler, callback_query_handler, error_handler

telegram_bp = Blueprint('telegram', __name__)
bot, dispatcher = None, None  # initialized when first request coming


@telegram_bp.route('/webhook', methods=['POST'])
def webhook_handler():
    update: Update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'


@telegram_bp.before_app_first_request
def bot_initialization():
    global bot, dispatcher
    bot = Bot(current_app.config['BOT_TOKEN'])
    dispatcher = Dispatcher(bot, None)

    dispatcher.add_handler(CallbackQueryHandler(callback_query_handler))
    dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))
    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('set_balance', set_balance_handler))
    dispatcher.add_handler(CommandHandler('balance', get_balance))
    dispatcher.add_handler(CommandHandler('month', month_command_handler))
    dispatcher.add_handler(CommandHandler('day', day_command_handler))
    dispatcher.add_handler(CommandHandler('cancel', cancel_handler))
    dispatcher.add_handler(CommandHandler('deposit', deposit_command_handler))
    dispatcher.add_error_handler(error_handler)


@telegram_bp.errorhandler(Exception)
def error_handler(e: Exception):
    current_app.logger.exception('Uncaught exception.')
    update: Update = telegram.Update.de_json(request.get_json(force=True), bot)
    update.message.reply_text('Whoops, looks like something went wrong.')
    return 'ok', 200
