"""
Media and delete handlers
Логика: редактирование медиа, удаление объекта
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.utils import (
    get_user, get_object, update_object, get_districts_config, get_rooms_config
)
from app.database import db
from bot.models import Object, ActionLog
from app.models.publication_history import PublicationHistory
from bot.handlers_object import (
    user_data, show_object_preview_with_menu, OBJECT_WAITING_AREA, OBJECT_WAITING_FLOOR,
    OBJECT_WAITING_COMMENT, OBJECT_WAITING_RENOVATION, OBJECT_WAITING_ADDRESS,
    OBJECT_WAITING_CONTACTS, OBJECT_WAITING_MEDIA
)

logger = logging.getLogger(__name__)

# Additional states for editing
OBJECT_WAITING_EDIT_ROOMS = 16
OBJECT_WAITING_EDIT_DISTRICT = 17
OBJECT_WAITING_EDIT_PRICE = 18
OBJECT_WAITING_ADD_DISTRICT = 19
OBJECT_WAITING_EDIT_AREA = 20
OBJECT_WAITING_EDIT_FLOOR = 21
OBJECT_WAITING_EDIT_COMMENT = 22
OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX = 24
OBJECT_PREVIEW_MENU = 23

async def add_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки добавления медиа"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("add_media_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [
        [InlineKeyboardButton("Пропустить", callback_data="skip_media")],
        [InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Отправьте фото объекта (можно несколько):", reply_markup=reply_markup)
    return OBJECT_WAITING_MEDIA


async def object_media_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка получения медиа"""
    # TODO: Implement media handling
    await update.message.reply_text("Обработка медиа пока не реализована.")
    return OBJECT_PREVIEW_MENU


async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить добавление медиа"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_object_from_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора объекта из списка для редактирования"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_object_from_list_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def contacts_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода контактов (phone или name)"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    text = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    
    # Check if waiting for contact name
    if user_data[user.id].get("waiting_contact_name"):
        user_data[user.id].pop("waiting_contact_name", None)
        update_object(object_id, {"contact_name": text})
        
        # Log action
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_contact_name_set',
                    details_json={'object_id': object_id, 'name': text},
                    created_at=datetime.utcnow()
                )
                db.session.add(action_log)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    else:
        # Phone input - валидация формата 89693386969
        phone = text
        import re
        phone_pattern = re.compile(r'^8\d{10}$')
        if not phone or not phone_pattern.match(phone):
            await update.message.reply_text("❌ Некорректный номер телефона. Номер должен быть в формате 89693386969 (11 цифр, начинается с 8).")
            return OBJECT_WAITING_CONTACTS
        
        update_object(object_id, {"phone_number": phone})
        
        # Log action
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_phone_set',
                    details_json={'object_id': object_id, 'phone': phone},
                    created_at=datetime.utcnow()
                )
                db.session.add(action_log)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    # Show contacts menu again with updated values
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS


async def contact_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени контакта"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    name = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    
    update_object(object_id, {"contact_name": name})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_contact_name_set',
                details_json={'object_id': object_id, 'name': name},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    # Show contacts menu again with updated values
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS


async def phone_from_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Использовать номер, имя и ник из настроек"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("phone_from_settings_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    user_obj = get_user(str(user.id))
    if not user_obj:
        await query.answer("Ошибка: пользователь не найден.", show_alert=True)
        return OBJECT_WAITING_CONTACTS
    
    # Get settings
    phone = user_obj.phone
    settings = user_obj.settings_json or {} if hasattr(user_obj, 'settings_json') else {}
    contact_name = settings.get('contact_name', '')
    show_username = settings.get('default_show_username', False)
    
    # Update object
    update_data = {}
    if phone:
        update_data['phone_number'] = phone
    if contact_name:
        update_data['contact_name'] = contact_name
    update_data['show_username'] = show_username
    
    update_object(object_id, update_data)
    
    # Log action
    try:
        action_log = ActionLog(
            user_id=user_obj.user_id,
            action='bot_object_contacts_from_settings',
            details_json={'object_id': object_id},
            created_at=datetime.utcnow()
        )
        db.session.add(action_log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    # Show contacts menu again with updated values
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS


async def phone_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Указать другой номер"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("phone_custom_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    user_data[user.id].pop("waiting_contact_name", None)
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите номер телефона в формате 89693386969:", reply_markup=reply_markup)
    return OBJECT_WAITING_CONTACTS


async def set_contact_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Указать имя контакта"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("set_contact_name_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    user_data[user.id]["waiting_contact_name"] = True
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите имя контакта:", reply_markup=reply_markup)
    return OBJECT_WAITING_CONTACTS


async def toggle_username_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить показ username"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("toggle_username_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    obj = get_object(object_id)
    if obj:
        current_value = obj.show_username or False
        update_object(object_id, {"show_username": not current_value})
        
        # Log action
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_show_username_toggled',
                    details_json={'object_id': object_id, 'show_username': not current_value},
                    created_at=datetime.utcnow()
                )
                db.session.add(action_log)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    # Show contacts menu again with updated values
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS


async def delete_object_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки удаления объекта"""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    
    try:
        await query.answer()
    except:
        pass
    
    object_id = query.data.replace("delete_object_", "")
    
    user = update.effective_user
    obj = get_object(object_id)
    
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return OBJECT_PREVIEW_MENU
    
    # Check ownership
    user_obj = get_user(str(user.id))
    if not user_obj or obj.user_id != user_obj.user_id:
        await query.answer("Вы можете удалять только свои объекты.", show_alert=True)
        return OBJECT_PREVIEW_MENU
    
    # Show confirmation
    rooms = obj.rooms_type or "Не указано"
    price = obj.price or 0
    
    text = f"⚠️ <b>Подтвердите удаление объекта:</b>\n\n"
    text += f"• {rooms} | {price} тыс. руб.\n\n"
    text += f"Это действие нельзя отменить!"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{object_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="back_to_preview")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error editing message for delete confirmation: {e}")
        try:
            if query.message:
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except:
            pass
    
    return OBJECT_PREVIEW_MENU


async def confirm_delete_object_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения удаления объекта"""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    
    try:
        await query.answer("Удаление...")
    except:
        pass
    
    object_id = query.data.replace("confirm_delete_", "")
    
    user = update.effective_user
    obj = get_object(object_id)
    
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return ConversationHandler.END
    
    # Check ownership
    user_obj = get_user(str(user.id))
    if not user_obj or obj.user_id != user_obj.user_id:
        await query.answer("Вы можете удалять только свои объекты.", show_alert=True)
        return ConversationHandler.END
    
    # Delete object
    try:
        # First, delete all related publication_history records
        # This prevents NOT NULL constraint violation
        # Use db.session.query() instead of Model.query for proper session handling
        db.session.query(PublicationHistory).filter_by(object_id=object_id).delete(synchronize_session=False)
        db.session.commit()
        
        # Log action before deletion
        try:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_deleted',
                details_json={'object_id': object_id},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log delete action: {e}")
        
        # Delete the object
        db.session.delete(obj)
        db.session.commit()
        
        # Clean up user_data
        if user.id in user_data:
            user_data[user.id].pop("object_id", None)
            user_data[user.id].pop("preview_message_id", None)
            user_data[user.id].pop("menu_message_id", None)
            user_data[user.id].pop("preview_chat_id", None)
        
        text = "✅ Объект успешно удален!"
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except:
            try:
                if query.message:
                    await query.message.reply_text(text, reply_markup=reply_markup)
            except:
                pass
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error deleting object: {e}", exc_info=True)
        db.session.rollback()
        await query.answer("Ошибка при удалении объекта.", show_alert=True)
        return OBJECT_PREVIEW_MENU
