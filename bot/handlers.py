"""
Bot handlers - основные обработчики команд
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_user, update_user_activity, generate_web_code
from bot.config import ADMIN_ID


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Update user activity
    update_user_activity(str(user.id), user.username)
    
    # Show main menu
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    keyboard = [
        [InlineKeyboardButton("Добавить объект", callback_data="add_object")],
        [InlineKeyboardButton("Мои объекты", callback_data="my_objects")],
        [InlineKeyboardButton("Настройки", callback_data="settings")],
        [InlineKeyboardButton("Получить код для веба", callback_data="getcode")],
    ]
    
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Добро пожаловать! Выберите действие:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def add_object_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать создание объекта"""
    # TODO: Implement object creation flow from botOLD.py
    await update.callback_query.answer("Функция в разработке")
    await update.callback_query.edit_message_text("Создание объекта будет реализовано позже")


async def getcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить код для привязки к веб-интерфейсу"""
    user_id = str(update.effective_user.id)
    
    try:
        code = generate_web_code(user_id)
        text = f"Ваш код для входа в веб-интерфейс:\n\n<b>{code}</b>\n\nКод действителен 10 минут."
        
        if update.message:
            await update.message.reply_text(text, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, parse_mode='HTML')
    except Exception as e:
        error_text = f"Ошибка при генерации кода: {str(e)}"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.answer(error_text, show_alert=True)

