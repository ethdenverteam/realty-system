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
    if query:
        await query.answer()
    
    user = update.effective_user
    user_obj = get_user(str(user.id))
    
    phone = user_obj.phone if user_obj else None
    contact_name = user_obj.settings_json.get('contact_name', '') if user_obj and user_obj.settings_json else None
    default_show_username = user_obj.settings_json.get('default_show_username', False) if user_obj and user_obj.settings_json else False
    
    text = "<b>⚙️ Настройки</b>\n\n"
    text += "<b>Настройка контактов</b>\n\n"
    text += f"Текущий номер: {phone if phone else 'Не указан'}\n"
    text += f"Имя: {contact_name if contact_name else 'Не указано'}\n"
    text += f"Указывать ник TG: {'Да' if default_show_username else 'Нет'}\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("Использовать номер из настроек", callback_data="settings_use_phone")],
        [InlineKeyboardButton("Указать другой номер", callback_data="settings_change_phone")],
        [InlineKeyboardButton("Указать имя", callback_data="settings_set_name")],
        [InlineKeyboardButton(f"Указывать ник TG: {'✅' if default_show_username else '❌'}", callback_data="settings_toggle_username")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
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
    
    # Сохранение номера - используем одну сессию для получения и обновления
    db = get_db()
    try:
        from bot.models import User
        user_obj = db.query(User).filter_by(telegram_id=int(user.id)).first()
        
        if not user_obj:
            # Create user if doesn't exist
            from bot.utils import update_user_activity
            update_user_activity(str(user.id), user.username)
            user_obj = db.query(User).filter_by(telegram_id=int(user.id)).first()
        
        if user_obj:
            user_obj.phone = phone
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
    
    # Return to settings menu
    await settings_handler(update, context)
    return SETTINGS_MENU


async def settings_use_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Использовать номер из настроек (заглушка, так как уже используется)"""
    query = update.callback_query
    await query.answer("Номер уже используется из настроек")
    return SETTINGS_MENU


async def settings_set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки указания имени"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("Введите ваше имя:", reply_markup=reply_markup)
    return SETTINGS_WAITING_NAME


async def settings_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени в настройках"""
    user = update.effective_user
    name = update.message.text.strip()
    
    db = get_db()
    try:
        from bot.models import User
        user_obj = db.query(User).filter_by(telegram_id=int(user.id)).first()
        
        if not user_obj:
            from bot.utils import update_user_activity
            update_user_activity(str(user.id), user.username)
            user_obj = db.query(User).filter_by(telegram_id=int(user.id)).first()
        
        if user_obj:
            if not user_obj.settings_json:
                user_obj.settings_json = {}
            user_obj.settings_json['contact_name'] = name
            db.commit()
            
            # Log action
            try:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_settings_name_updated',
                    details_json={'name': name},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log action: {e}")
                db.rollback()
    finally:
        db.close()
    
    await update.message.reply_text("✅ Имя сохранено!")
    
    # Show settings menu again
    user_obj = get_user(str(update.effective_user.id))
    phone = user_obj.phone if user_obj else None
    contact_name = user_obj.settings_json.get('contact_name', '') if user_obj and user_obj.settings_json else None
    default_show_username = user_obj.settings_json.get('default_show_username', False) if user_obj and user_obj.settings_json else False
    
    text = "<b>⚙️ Настройки</b>\n\n"
    text += "<b>Настройка контактов</b>\n\n"
    text += f"Текущий номер: {phone if phone else 'Не указан'}\n"
    text += f"Имя: {contact_name if contact_name else 'Не указано'}\n"
    text += f"Указывать ник TG: {'Да' if default_show_username else 'Нет'}\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("Использовать номер из настроек", callback_data="settings_use_phone")],
        [InlineKeyboardButton("Указать другой номер", callback_data="settings_change_phone")],
        [InlineKeyboardButton("Указать имя", callback_data="settings_set_name")],
        [InlineKeyboardButton(f"Указывать ник TG: {'✅' if default_show_username else '❌'}", callback_data="settings_toggle_username")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    return SETTINGS_MENU


async def settings_toggle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить показ username по умолчанию"""
    query = update.callback_query
    await query.answer()
    
    db = get_db()
    try:
        from bot.models import User
        user_obj = db.query(User).filter_by(telegram_id=int(update.effective_user.id)).first()
        
        if user_obj:
            if not user_obj.settings_json:
                user_obj.settings_json = {}
            current_value = user_obj.settings_json.get('default_show_username', False)
            user_obj.settings_json['default_show_username'] = not current_value
            db.commit()
            
            # Log action
            try:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_settings_username_toggled',
                    details_json={'default_show_username': not current_value},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log action: {e}")
                db.rollback()
    finally:
        db.close()
    
    await settings_handler(update, context)
    return SETTINGS_MENU


def create_settings_conversation_handler():
    """Create conversation handler for settings"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(settings_handler, pattern="^settings$")],
        states={
            SETTINGS_MENU: [
                CallbackQueryHandler(settings_change_phone, pattern="^settings_change_phone$"),
                CallbackQueryHandler(settings_use_phone, pattern="^settings_use_phone$"),
                CallbackQueryHandler(settings_set_name, pattern="^settings_set_name$"),
                CallbackQueryHandler(settings_toggle_username, pattern="^settings_toggle_username$"),
                CallbackQueryHandler(settings_handler, pattern="^settings$"),
            ],
            SETTINGS_WAITING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_phone_input),
            ],
            SETTINGS_WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_name_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(settings_handler, pattern="^settings$"),
            MessageHandler(filters.COMMAND, settings_handler)
        ],
        name="settings_handler"
    )

