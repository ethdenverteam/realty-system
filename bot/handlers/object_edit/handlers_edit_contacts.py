"""
Contacts editing handlers
Логика: редактирование контактов
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

async def edit_contacts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования контактов"""
    query = update.callback_query
    user = update.effective_user
    
    # Extract object_id from callback_data or user_data
    object_id = None
    if query and query.data:
        try:
            if query.data.startswith("edit_contacts_"):
                object_id = query.data.replace("edit_contacts_", "")
            else:
                # Try to get from user_data if callback_data doesn't match
                if user.id in user_data and "object_id" in user_data[user.id]:
                    object_id = user_data[user.id]["object_id"]
        except Exception as e:
            logger.error(f"Error parsing callback_data: {e}, data: {query.data if query else None}")
    else:
        # Called from message handler - get object_id from user_data
        if user.id in user_data and "object_id" in user_data[user.id]:
            object_id = user_data[user.id]["object_id"]
    
    if not object_id:
        error_text = "Ошибка: не удалось определить объект для редактирования."
        if query:
            try:
                await query.answer(error_text, show_alert=True)
            except:
                pass
        elif update.message:
            await update.message.reply_text(error_text)
        return ConversationHandler.END
    
    if query:
        try:
            await query.answer()
        except:
            pass
    
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    # Don't delete preview when editing contacts - keep it visible
    # await delete_preview_and_menu(context, user.id)
    
    obj = get_object(object_id)
    user_obj = get_user(str(user.id))
    
    phone = obj.phone_number if obj else None
    if not phone and user_obj:
        phone = user_obj.phone
    
    contact_name = obj.contact_name if obj else ""
    show_username = obj.show_username if obj else False
    
    text = f"<b>Настройка контактов</b>\n\n"
    text += f"Текущий номер: {phone if phone else 'Не указан'}\n"
    text += f"Имя: {contact_name if contact_name else 'Не указано'}\n"
    text += f"Указывать ник TG: {'Да' if show_username else 'Нет'}\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("Использовать номер из настроек", callback_data=f"phone_from_settings_{object_id}")],
        [InlineKeyboardButton("Указать другой номер", callback_data=f"phone_custom_{object_id}")],
        [InlineKeyboardButton("Указать имя", callback_data=f"set_contact_name_{object_id}")],
        [InlineKeyboardButton(f"Указывать ник TG: {'✅' if show_username else '❌'}", callback_data=f"toggle_username_{object_id}")],
        [InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            try:
                # Try to reply to the message instead
                if query.message:
                    await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    # Last resort - send new message
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            except Exception as e2:
                logger.error(f"Error sending contacts menu fallback: {e2}")
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except Exception as e3:
                    logger.error(f"Error sending contacts menu final fallback: {e3}")
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        # Fallback - try to send to user
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending contacts menu: {e}")
    
    return OBJECT_WAITING_CONTACTS


async def edit_rooms_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования комнат"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_rooms_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    rooms = get_rooms_config()
    keyboard = []
    row = []
    for i, room in enumerate(rooms):
        row.append(InlineKeyboardButton(room, callback_data=f"rooms_{room}"))
        if len(row) == 3 or i == len(rooms) - 1:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🏠 Выберите тип комнат:", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_ROOMS


async def edit_rooms_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа комнат"""
    query = update.callback_query
    await query.answer()
    
    rooms_type = query.data.replace("rooms_", "")
    
    user = update.effective_user
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    update_object(object_id, {"rooms_type": rooms_type})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_rooms_updated',
                details_json={'object_id': object_id, 'rooms_type': rooms_type},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования районов"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_district_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    obj = get_object(object_id)
    current_districts = obj.districts_json or [] if obj else []
    
    districts = get_districts_config()
    keyboard = []
    for district in districts:
        is_selected = district in current_districts
        button_text = f"{'✅' if is_selected else '⬜'} {district}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"district_{district}")])
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🏘️ Выберите районы (нажмите для переключения):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_DISTRICT


async def edit_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района при редактировании"""
    query = update.callback_query
    await query.answer()
    
    district = query.data.replace("district_", "")
    
    user = update.effective_user
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    obj = get_object(object_id)
    
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return ConversationHandler.END
    
    current_districts = list(obj.districts_json or [])
    
    if district in current_districts:
        current_districts.remove(district)
    else:
        current_districts.append(district)
    
    update_object(object_id, {"districts_json": current_districts})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_districts_updated',
                details_json={'object_id': object_id, 'districts': current_districts},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def add_district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки добавления района"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("add_district_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    districts = get_districts_config()
    keyboard = []
    for district in districts:
        keyboard.append([InlineKeyboardButton(district, callback_data=f"district_{district}")])
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🏘️ Выберите район для добавления:", reply_markup=reply_markup)
    return OBJECT_WAITING_ADD_DISTRICT


async def add_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района при добавлении"""
    query = update.callback_query
    await query.answer()
    
    district = query.data.replace("district_", "")
    
    user = update.effective_user
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    obj = get_object(object_id)
    
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        return ConversationHandler.END
    
    current_districts = list(obj.districts_json or [])
    
    if district not in current_districts:
        current_districts.append(district)
        update_object(object_id, {"districts_json": current_districts})
        
        # Log action
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_district_added',
                    details_json={'object_id': object_id, 'district': district},
                    created_at=datetime.utcnow()
                )
                db.session.add(action_log)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


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


