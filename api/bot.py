import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
    CallbackQueryHandler, ConversationHandler
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "123456789"))
ASK_NICK, ASK_DISCORD, ASK_SCREEN = range(3)
WALLET = "TVadXnyCDphgsSZY4p9zs3pgNZYufRwp71"

# Создаем приложение глобально
application = Application.builder().token(TOKEN).build()

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
            "👉 Нажмите на адрес выше или кнопку ниже для копирования."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == "copy_wallet":
        # Отправляем адрес отдельным сообщением для удобного копирования
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"`{WALLET}`",
            parse_mode='Markdown'
        )
        await query.answer("💳 Адрес отправлен для копирования!", show_alert=True)
    
    elif query.data == "back":
        keyboard = [[InlineKeyboardButton("Оплатить", callback_data="pay")]]
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
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, отправьте именно скриншот.")
        return ASK_SCREEN

# ConversationHandler с правильными настройками
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
    allow_reentry=True,
    per_message=False,  # Добавляем явно для избегания warning
    per_chat=True,
    per_user=True
)

# Добавляем хендлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(conv_handler)

# Основная функция для Vercel
async def handler(request):
    try:
        # Получаем тело запроса
        if hasattr(request, 'get_json'):
            body = await request.get_json()
        else:
            body = json.loads(await request.body())
        
        # Создаем Update объект
        update = Update.de_json(body, application.bot)
        
        # Обрабатываем обновление
        await application.process_update(update)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "ok"})
        }
    except Exception as e:
        print(f"Error processing update: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }

# Для совместимости с разными форматами Vercel
def main(request):
    import asyncio
    return asyncio.run(handler(request))
