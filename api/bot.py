from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)
import os
import asyncio
import json

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "123456789"))
ASK_NICK, ASK_DISCORD, ASK_SCREEN = range(3)
application = None

WALLET = "TVadXnyCDphgsSZY4p9zs3pgNZYufRwp71"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Оплатить", callback_data="pay")]]
    text = (
        "Трейдинг — одиночная игра.\n"
        "Но правильное окружение подталкивает к развитию и делает эту игру понятнее.\n\n"
        "*Что получает участник:*\n"
        "https://teletype.in/@jteam/xJTC\n\n"
        "*Цена:* 200 USDT (3 месяца)\n\n"
        "Актуально до 1 июня."
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ... (остальной async код оставь без изменений)

def setup_bot():
    global application
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button, pattern="^paid$")
        ],
        states={
            ASK_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nick)],
            ASK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discord)],
            ASK_SCREEN: [MessageHandler(filters.PHOTO, ask_screen)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(conv_handler)

setup_bot()

async def handler(request, context):
    body = await request.json()
    update = Update.de_json(body, application.bot)
    await application.process_update(update)
    return {
        "statusCode": 200,
        "body": "ok"
    }
