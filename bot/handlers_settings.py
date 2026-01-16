"""
Settings handlers for bot
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.utils import get_user, save_user
from bot.database import get_db
from bot.models import ActionLog

logger = logging.getLogger(__name__)

# Conversation states for settings
SETTINGS_MENU = 30
SETTINGS_WAITING_PHONE = 31


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки настроек"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_obj = get_user(str(user.id))
    
    phone = user_obj.phone if user_obj else None
    
    text = "<b>⚙️ Настройки</b>\n\n"
    text += f"Номер телефона: {phone if phone else 'Не указан'}\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("📱 Изменить номер телефона", callback_data="settings_change_phone")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    return SETTINGS_MENU


async def settings_change_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки изменения номера телефона"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "Введите номер телефона:\n\n"
    text += "Номер в формате:\n"
    text += "89693386969"
    
    await query.message.reply_text(text, reply_markup=reply_markup)
    return SETTINGS_WAITING_PHONE


async def settings_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода номера телефона в настройках"""
    user = update.effective_user
    phone = update.message.text.strip()
    
    # Простая валидация номера
    if not phone or len(phone) < 10:
        text = "❌ Некорректный номер телефона. Попробуйте еще раз.\n\n"
        text += "Номер в формате:\n"
        text += "89693386969"
        keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
        return SETTINGS_WAITING_PHONE
    
    # Сохранение номера
    user_obj = get_user(str(user.id))
    if not user_obj:
        # Create user if doesn't exist
        from bot.utils import update_user_activity
        update_user_activity(str(user.id), user.username)
        user_obj = get_user(str(user.id))
    
    if user_obj:
        user_obj.phone = phone
        db = get_db()
        try:
            db.commit()
            
            # Log action
            try:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_settings_phone_updated',
                    details_json={'phone': phone},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log action: {e}")
                db.rollback()
        finally:
            db.close()
    
    await update.message.reply_text("✅ Номер телефона сохранен!")
    
    # Return to main menu
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    return ConversationHandler.END


def create_settings_conversation_handler():
    """Create conversation handler for settings"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(settings_handler, pattern="^settings$")],
        states={
            SETTINGS_MENU: [
                CallbackQueryHandler(settings_change_phone, pattern="^settings_change_phone$"),
                CallbackQueryHandler(settings_handler, pattern="^settings$"),
            ],
            SETTINGS_WAITING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_phone_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(settings_handler, pattern="^settings$"),
            MessageHandler(filters.COMMAND, settings_handler)
        ],
        name="settings_handler"
    )

