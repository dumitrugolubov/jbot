import os
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "123456789"))  # Твой Telegram ID

ASK_NICK, ASK_DISCORD, ASK_SCREEN = range(3)

app = Flask(__name__)
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Что входит?", callback_data="features")],
        [InlineKeyboardButton("Оплатить", callback_data="pay")]
    ]
    await update.message.reply_text(
        "👋 Добро пожаловать! JTC | Discord — бот для подписок.\n\nНажмите кнопку для оплаты.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "features":
        await query.edit_message_text(
            "🔑 В подписку входит: ... (тут опиши список фич)\n\nНажмите «Оплатить», чтобы получить реквизиты."
        )
    elif query.data == "pay":
        await query.edit_message_text(
            "💸 Переведите оплату по этим реквизитам: ...\n\nПосле оплаты нажмите «Оплатил».",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Оплатил", callback_data="paid")],
                [InlineKeyboardButton("Отмена", callback_data="cancel")]
            ])
        )
    elif query.data == "paid":
        await query.edit_message_text(
            "✍️ Введите ваш Telegram никнейм:"
        )
        return ASK_NICK
    elif query.data == "cancel":
        await query.edit_message_text("❌ Отменено.")
        return ConversationHandler.END

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
        # Пересылаем админу
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=file_id,
            caption=f"🧑 Новый платёж\nTG: {tg_nick}\nDiscord: {discord_nick}"
        )
        await update.message.reply_text("Спасибо! Ваша заявка отправлена на проверку.", reply_markup=ReplyKeyboardRemove())
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
        application.update_queue.put(update)
        return "ok"
    return "fail"

# Для локального теста можно добавить app.run() (на Vercel не нужно)
