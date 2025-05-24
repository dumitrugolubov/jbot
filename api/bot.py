import os
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)
import asyncio

TOKEN = os.environ.get("8103528030:AAGE4ex7SrD15eLgdOpi0vgX4UTX-N0tcKQ")
ADMIN_CHAT_ID = int(os.environ.get("412870818", "123456789"))

ASK_NICK, ASK_DISCORD, ASK_SCREEN = range(3)

app = Flask(__name__)
application = None

WALLET = "TVadXnyCDphgsSZY4p9zs3pgNZYufRwp71"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Оплатить", callback_data="pay")]
    ]
    text = (
        "Трейдинг — одиночная игра.\n"
        "Но правильное окружение подталкивает к развитию и делает эту игру понятнее.\n\n"
        "*Что получает участник:*\n"
        "https://teletype.in/@jteam/xJTC\n\n"
        "*Цена:* 200 USDT (3 месяца)\n\n"
        "Актуально до 1 июня."
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "pay":
        keyboard = [
            [InlineKeyboardButton("Оплатил", callback_data="paid")],
            [InlineKeyboardButton("Назад", callback_data="back")]
        ]
        text = (
            "*Реквизиты:*\n\n"
            "USDT (TRC20)\n\n"
            f"`{WALLET}`\n\n"
            "👉 Нажмите и удерживайте адрес, чтобы скопировать."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("Оплатить", callback_data="pay")]
        ]
        text = (
            "Трейдинг — одиночная игра.\n"
            "Но правильное окружение подталкивает к развитию и делает эту игру понятнее.\n\n"
            "*Что получает участник:*\n"
            "https://teletype.in/@jteam/xJTC\n\n"
            "*Цена:* 200 USDT (3 месяца)\n\n"
            "Актуально до 1 июня."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == "paid":
        await query.edit_message_text("✍️ Введите ваш Telegram никнейм:")
        return ASK_NICK

async def ask_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tg_nick"] = update.message.text
    await update.message.reply_text("Введите ваш Discord никнейм:")
    return ASK_DISCORD

async def ask_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["discord_nick"] = update.message.text
    await update.message.reply_text("Загрузите скрин оплаты:")
    return ASK_SCREEN

async def ask_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        file_id = photo_file.file_id
        tg_nick = context.user_data.get("tg_nick", "")
        discord_nick = context.user_data.get("discord_nick", "")
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=file_id,
            caption=f"🧑 Новый платёж\nTG: {tg_nick}\nDiscord: {discord_nick}"
        )
        final_text = (
            "____\n\n"
            "Готово!\n\n"
            "Как только менеджер проверит заявку, вы сразу получите ссылку и инструкции.\n\n"
            "Пока можете расслабиться и посмотреть видео лучшего YouTube блогера по трейдингу:\n"
            "https://youtube.com/@jteamtube\n\n"
            "____"
        )
        await update.message.reply_text(final_text, reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Пожалуйста, отправьте именно скриншот.")
        return ASK_SCREEN
    return ConversationHandler.END

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

@app.route("/api/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.get_event_loop().create_task(application.process_update(update))
        return "ok"
    return "fail"
