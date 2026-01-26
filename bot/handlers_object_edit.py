"""
Object editing handlers for bot
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.utils import (
    get_user, get_object, update_object, get_districts_config, get_rooms_config
)
from bot.database import get_db
from bot.models import Object, ActionLog
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
OBJECT_PREVIEW_MENU = 23


async def delete_preview_and_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Удалить превью и меню объекта"""
    if user_id in user_data:
        chat_id = user_data[user_id].get("preview_chat_id")
        preview_id = user_data[user_id].get("preview_message_id")
        menu_id = user_data[user_id].get("menu_message_id")
        
        if chat_id and preview_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=preview_id)
            except:
                pass
            user_data[user_id].pop("preview_message_id", None)
        
        if chat_id and menu_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=menu_id)
            except:
                pass
            user_data[user_id].pop("menu_message_id", None)


async def back_to_preview_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к предпросмотру"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    elif update.message:
        pass
    else:
        return ConversationHandler.END
    
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        if update.callback_query:
            await update.callback_query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    obj = get_object(object_id)
    user_obj = get_user(str(user.id))
    
    if not obj:
        if update.callback_query:
            await update.callback_query.edit_message_text("Ошибка: объект не найден.")
        return ConversationHandler.END
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


# Edit handlers
async def edit_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования цены"""
    query = update.callback_query
    await query.answer()
    
    # Extract object_id from callback_data
    object_id = query.data.replace("edit_price_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("💰 Введите цену в тысячах рублей:", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_PRICE


async def edit_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода цены при редактировании"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        
        object_id = user_data[user.id]["object_id"]
        update_object(object_id, {"price": price})
        
        # Log action
        try:
            db = get_db()
            try:
                user_obj = get_user(str(user.id))
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_price_edited',
                        details_json={'object_id': object_id, 'price': price},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
        
        await show_object_preview_with_menu(update, context, object_id)
        return OBJECT_PREVIEW_MENU
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат цены. Введите число больше нуля:")
        return OBJECT_WAITING_EDIT_PRICE


async def edit_area_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования площади"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_area_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("📐 Введите площадь в м²:", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_AREA


async def edit_area_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода площади при редактировании"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    try:
        area = float(update.message.text.replace(",", "."))
        if area <= 0:
            raise ValueError
        
        object_id = user_data[user.id]["object_id"]
        update_object(object_id, {"area": area})
        
        # Log action
        try:
            db = get_db()
            try:
                user_obj = get_user(str(user.id))
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_area_edited',
                        details_json={'object_id': object_id, 'area': area},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
        
        await show_object_preview_with_menu(update, context, object_id)
        return OBJECT_PREVIEW_MENU
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат площади. Введите число больше нуля:")
        return OBJECT_WAITING_EDIT_AREA


async def edit_floor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования этажа"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_floor_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🏢 Введите этаж (например: 5/9):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_FLOOR


async def edit_floor_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода этажа при редактировании"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    floor = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    
    update_object(object_id, {"floor": floor})
    
    # Log action
    try:
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_floor_edited',
                    details_json={'object_id': object_id, 'floor': floor},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования комментария"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_comment_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("📝 Введите описание (комментарий):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_COMMENT


async def edit_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода комментария при редактировании"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    comment = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    
    update_object(object_id, {"comment": comment})
    
    # Log action
    try:
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_comment_edited',
                    details_json={'object_id': object_id, 'comment': comment},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_renovation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования ремонта"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_renovation_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    renovations = ["Черновая", "ПЧО", "Ремонт требует освежения", "Хороший ремонт", "Инстаграмный"]
    keyboard = [[InlineKeyboardButton(ren, callback_data=f"renovation_{ren}")] for ren in renovations]
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("🛋 Выберите состояние ремонта:", reply_markup=reply_markup)
    return OBJECT_WAITING_RENOVATION


async def renovation_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора состояния ремонта"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    renovation = query.data.replace("renovation_", "")
    object_id = user_data[user.id]["object_id"]
    
    update_object(object_id, {"renovation": renovation})
    
    # Log action
    try:
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_renovation_set',
                    details_json={'object_id': object_id, 'renovation': renovation},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования адреса"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_address_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("📍 Введите адрес (улица или улица + номер дома):", reply_markup=reply_markup)
    return OBJECT_WAITING_ADDRESS


async def edit_contacts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования контактов"""
    query = update.callback_query
    if query:
        await query.answer()
        object_id = query.data.replace("edit_contacts_", "")
    else:
        # Called from message handler - get object_id from user_data
        user = update.effective_user
        if user.id not in user_data or "object_id" not in user_data[user.id]:
            return
        object_id = user_data[user.id]["object_id"]
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
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
        except:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
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
    """Обработка выбора комнат при редактировании"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    rooms_type = query.data.replace("rooms_", "")
    object_id = user_data[user.id]["object_id"]
    
    update_object(object_id, {"rooms_type": rooms_type})
    
    # Log action
    try:
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_rooms_edited',
                    details_json={'object_id': object_id, 'rooms_type': rooms_type},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования района"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_district_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    obj = get_object(object_id)
    if obj:
        user_data[user.id]["districts"] = obj.districts_json or []
        # Clear districts
        update_object(object_id, {"districts_json": []})
    
    await delete_preview_and_menu(context, user.id)
    
    districts_config = get_districts_config()
    districts = list(districts_config.keys()) if districts_config else []
    
    keyboard = [[InlineKeyboardButton(district, callback_data=f"district_{district}")] 
                for district in districts]
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("📍 Выберите район (текущие районы очищены):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_DISTRICT


async def edit_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района при редактировании"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    district = query.data.replace("district_", "")
    object_id = user_data[user.id]["object_id"]
    
    if "districts" not in user_data[user.id]:
        user_data[user.id]["districts"] = []
    
    if district not in user_data[user.id]["districts"]:
        user_data[user.id]["districts"].append(district)
    
    update_object(object_id, {"districts_json": user_data[user.id]["districts"]})
    
    # Log action
    try:
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_district_edited',
                    details_json={'object_id': object_id, 'district': district},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
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
    
    obj = get_object(object_id)
    if obj:
        user_data[user.id]["districts"] = obj.districts_json or []
    
    await delete_preview_and_menu(context, user.id)
    
    districts_config = get_districts_config()
    districts = list(districts_config.keys()) if districts_config else []
    
    keyboard = [[InlineKeyboardButton(district, callback_data=f"district_{district}")] 
                for district in districts]
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text("📍 Выберите район для добавления:", reply_markup=reply_markup)
    return OBJECT_WAITING_ADD_DISTRICT


async def add_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района для добавления"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await query.edit_message_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    district = query.data.replace("district_", "")
    object_id = user_data[user.id]["object_id"]
    
    obj = get_object(object_id)
    current_districts = obj.districts_json or [] if obj else []
    
    if district not in current_districts:
        current_districts.append(district)
        update_object(object_id, {"districts_json": current_districts})
        user_data[user.id]["districts"] = current_districts
        
        # Log action
        try:
            db = get_db()
            try:
                user_obj = get_user(str(user.id))
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_district_added',
                        details_json={'object_id': object_id, 'district': district},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
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
    
    obj = get_object(object_id)
    current_photos = obj.photos_json or [] if obj else []
    
    # Clear existing photos
    update_object(object_id, {"photos_json": []})
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [
        [InlineKeyboardButton("Пропустить", callback_data="skip_media")],
        [InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "📷 Отправьте фото объекта (до 10 фото). Нажмите 'Пропустить' если фото нет:",
        reply_markup=reply_markup
    )
    return OBJECT_WAITING_MEDIA


async def address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода адреса"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    address = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    
    update_object(object_id, {"address": address})
    
    # Log action
    try:
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_address_set',
                    details_json={'object_id': object_id, 'address': address},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
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
            db = get_db()
            try:
                user_obj = get_user(str(user.id))
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_contact_name_set',
                        details_json={'object_id': object_id, 'name': text},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    else:
        # Phone input
        phone = text
        if not phone or len(phone) < 10:
            await update.message.reply_text("❌ Некорректный номер телефона. Попробуйте еще раз.")
            return OBJECT_WAITING_CONTACTS
        
        update_object(object_id, {"phone_number": phone})
        
        # Log action
        try:
            db = get_db()
            try:
                user_obj = get_user(str(user.id))
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_phone_set',
                        details_json={'object_id': object_id, 'phone': phone},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
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
        db = get_db()
        try:
            user_obj = get_user(str(user.id))
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_contact_name_set',
                    details_json={'object_id': object_id, 'name': name},
                    created_at=datetime.utcnow()
                )
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    # Show contacts menu again with updated values
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS


async def phone_from_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Использовать номер из настроек"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("phone_from_settings_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    user_obj = get_user(str(user.id))
    phone = user_obj.phone if user_obj else None
    
    if phone:
        update_object(object_id, {"phone_number": phone})
        
        # Log action
        try:
            db = get_db()
            try:
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_phone_set_from_settings',
                        details_json={'object_id': object_id, 'phone': phone},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
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
    
    await delete_preview_and_menu(context, user.id)
    
    text = "Введите номер телефона:\n\n"
    text += "Номер в формате:\n"
    text += "89693386969"
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(text, reply_markup=reply_markup)
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
            db = get_db()
            try:
                user_obj = get_user(str(user.id))
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_show_username_toggled',
                        details_json={'object_id': object_id, 'show_username': not current_value},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    # Show contacts menu again with updated values
    await edit_contacts_handler(update, context)
    return OBJECT_WAITING_CONTACTS

