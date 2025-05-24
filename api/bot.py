import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
    CallbackQueryHandler, ConversationHandler
)
import httpx # Рекомендуется для асинхронных HTTP-запросов (если понадобится, например, для OpenRouter)

# --- Константы и конфигурация ---
# Получайте токены из переменных окружения Vercel.
# Настройте их в Dashboard Vercel как "Secret Environment Variables".
# Пример: TELEGRAM_TOKEN, ADMIN_CHAT_ID
TOKEN = os.environ.get("TELEGRAM_TOKEN")
# chat_id для админа. Убедитесь, что это число.
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID")) # Укажите ID админа по умолчанию или оставьте пустым
WALLET = "TVadXnyCDphgsSZY4p9zs3pgNZYufRwp71" # Адрес вашего кошелька USDT

# Состояния для ConversationHandler
ASK_NICK, ASK_DISCORD, ASK_SCREEN = range(3)

# --- Глобальная переменная для экземпляра Application ---
# Это гарантирует, что Application будет создан только один раз
# при "холодном" запуске сервера Vercel.
_application_instance = None

def get_application():
    """
    Инициализирует и возвращает экземпляр telegram.ext.Application.
    Инициализация происходит только один раз.
    """
    global _application_instance
    if _application_instance is None:
        if not TOKEN:
            raise ValueError("TELEGRAM_TOKEN не установлен в переменных окружения.")
        _application_instance = Application.builder().token(TOKEN).build()
        setup_handlers(_application_instance) # Регистрируем обработчики при создании Application
    return _application_instance

# --- Функции-обработчики для бота ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок InlineKeyboard."""
    query = update.callback_query
    await query.answer() # Всегда отвечаем на callback_query, чтобы убрать "часики" на кнопке

    if query.data == "pay":
        keyboard = [
            [InlineKeyboardButton("📋 Копировать адрес", callback_data="copy_wallet")],
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
        # Отправляем адрес как отдельное сообщение для удобства копирования
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"`{WALLET}`",
            parse_mode='Markdown'
        )
        await query.answer("💳 Адрес отправлен для копирования!", show_alert=True)

    elif query.data == "back":
        # Возвращаем к начальному состоянию с кнопкой "Оплатить"
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
        return ASK_NICK # Переход к следующему состоянию ConversationHandler

async def ask_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода никнейма Telegram."""
    context.user_data["tg_nick"] = update.message.text
    await update.message.reply_text("Введите ваш Discord никнейм:")
    return ASK_DISCORD

async def ask_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода никнейма Discord."""
    context.user_data["discord_nick"] = update.message.text
    await update.message.reply_text("Загрузите скрин оплаты:")
    return ASK_SCREEN

async def ask_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки скриншота оплаты."""
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        file_id = photo_file.file_id
        tg_nick = context.user_data.get("tg_nick", "Не указан")
        discord_nick = context.user_data.get("discord_nick", "Не указан")

        # Отправка скриншота админу
        try:
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=file_id,
                caption=f"🧑 Новый платёж\nTG: {tg_nick}\nDiscord: {discord_nick}\n"
                        f"Пользователь: {update.effective_user.mention_html()}", # Добавлено упоминание пользователя
                parse_mode='HTML' # Для корректного отображения mention_html
            )
        except Exception as e:
            # Логируем ошибку, если не удалось отправить админу
            print(f"Ошибка при отправке фото админу ({ADMIN_CHAT_ID}): {e}")
            await update.message.reply_text("Произошла ошибка при отправке данных. Пожалуйста, свяжитесь с поддержкой.")
            return ConversationHandler.END # Завершаем диалог

        final_text = (
            "____\n\n"
            "Готово!\n\n"
            "Как только менеджер проверит заявку, вы сразу получите ссылку и инструкции.\n\n"
            "Пока можете расслабиться и посмотреть видео лучшего YouTube блогера по трейдингу:\n"
            "https://youtube.com/@jteamtube\n\n" # Убедитесь, что это реальная ссылка
            "____"
        )
        await update.message.reply_text(final_text, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END # Завершаем диалог
    else:
        # Если пришло не фото, просим отправить именно скриншот
        await update.message.reply_text("Пожалуйста, отправьте именно скриншот.")
        return ASK_SCREEN

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /cancel для выхода из ConversationHandler."""
    await update.message.reply_text(
        'Диалог отменён. Вы можете начать заново, нажав /start.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для неизвестных команд."""
    await update.message.reply_text("Извините, я не понимаю эту команду. Попробуйте /start.")


# --- Настройка обработчиков ---

def setup_handlers(application: Application):
    """Регистрирует все обработчики для бота."""
    # ConversationHandler для процесса оплаты
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_callback, pattern="^paid$") # Начинаем диалог по кнопке "Оплатил"
        ],
        states={
            ASK_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nick)],
            ASK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discord)],
            # Обрабатываем фото, а также любые другие сообщения, если это не фото
            ASK_SCREEN: [
                MessageHandler(filters.PHOTO, ask_screen),
                MessageHandler(filters.TEXT | filters.ATTACHMENT | filters.VIDEO | filters.AUDIO | filters.VOICE, ask_screen)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)], # Возможность отменить диалог
        allow_reentry=True, # Позволяет повторно входить в диалог
        per_user=True, # Диалог привязан к конкретному пользователю
        per_chat=False # Если бот в группах, то True, иначе False
    )

    # Добавляем все обработчики в приложение
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback)) # Обработчик для всех других Inline-кнопок
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command)) # Отлов неизвестных команд

# --- Основная точка входа для Vercel ---

async def handle_telegram_update(body: dict) -> dict:
    """
    Асинхронная функция для обработки входящих HTTP-запросов от Telegram (webhook).
    Десериализует тело запроса в объект Update и передает его боту.
    """
    try:
        application = get_application()
        update = Update.de_json(body, application.bot) # Преобразуем JSON в объект Update
        await application.process_update(update) # Обрабатываем обновление через Application
        return {"statusCode": 200, "body": "OK"} # Возвращаем успешный ответ Telegram
    except Exception as e:
        print(f"Error processing Telegram update: {e}")
        # Возвращаем 500 Internal Server Error, если что-то пошло не так
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# --- Главная функция-обработчик для Vercel (синхронный адаптер) ---
# Vercel вызывает эту функцию, когда приходит HTTP-запрос.
# Она должна быть синхронной, если не настроен ASGI (который более сложен в настройке для PTB).
def handler(request):
    """
    Главная функция-обработчик, вызываемая Vercel.
    Парсит входящий HTTP-запрос и запускает
