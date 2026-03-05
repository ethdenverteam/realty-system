"""
Basic object editing handlers
Логика: редактирование базовых полей (цена, площадь, этаж, комментарий, ЖК, ремонт)
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
    """Вернуться к превью объекта"""
    user = update.effective_user
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        if update.callback_query:
            await update.callback_query.answer("Ошибка: данные объекта не найдены.", show_alert=True)
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования цены"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_price_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите новую цену (тыс. руб.):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_PRICE


async def edit_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода цены"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.strip())
        if price < 0:
            await update.message.reply_text("Цена не может быть отрицательной.")
            return OBJECT_WAITING_EDIT_PRICE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return OBJECT_WAITING_EDIT_PRICE
    
    object_id = user_data[user.id]["object_id"]
    update_object(object_id, {"price": price})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_price_updated',
                details_json={'object_id': object_id, 'price': price},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


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
    await query.message.reply_text("Введите новую площадь (м²):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_AREA


async def edit_area_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода площади"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    try:
        area = float(update.message.text.strip())
        if area < 0:
            await update.message.reply_text("Площадь не может быть отрицательной.")
            return OBJECT_WAITING_EDIT_AREA
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число.")
        return OBJECT_WAITING_EDIT_AREA
    
    object_id = user_data[user.id]["object_id"]
    update_object(object_id, {"area": area})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_area_updated',
                details_json={'object_id': object_id, 'area': area},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


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
    await query.message.reply_text("Введите этаж (например: 5/9):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_FLOOR


async def edit_floor_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода этажа"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    floor = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    update_object(object_id, {"floor": floor})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_floor_updated',
                details_json={'object_id': object_id, 'floor': floor},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
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
    await query.message.reply_text("Введите комментарий:", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_COMMENT


async def edit_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода комментария"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    comment = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    update_object(object_id, {"comment": comment})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_comment_updated',
                details_json={'object_id': object_id, 'comment': comment[:100]},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU


async def edit_residential_complex_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки редактирования ЖК"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("edit_residential_complex_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    await delete_preview_and_menu(context, user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Введите название жилого комплекса (ЖК):", reply_markup=reply_markup)
    return OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX


async def residential_complex_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ЖК"""
    user = update.effective_user
    
    if user.id not in user_data or "object_id" not in user_data[user.id]:
        await update.message.reply_text("Ошибка: данные объекта не найдены.")
        return ConversationHandler.END
    
    residential_complex = update.message.text.strip()
    object_id = user_data[user.id]["object_id"]
    update_object(object_id, {"residential_complex": residential_complex if residential_complex else None})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_residential_complex_updated',
                details_json={'object_id': object_id, 'residential_complex': residential_complex},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
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
    
    # Варианты ремонта
    renovation_options = [
        "Евроремонт",
        "Косметический",
        "Без ремонта",
        "Требует ремонта"
    ]
    
    keyboard = []
    for option in renovation_options:
        keyboard.append([InlineKeyboardButton(option, callback_data=f"renovation_{option}_{object_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выберите состояние ремонта:", reply_markup=reply_markup)
    return OBJECT_WAITING_RENOVATION  # Ожидаем выбора ремонта


async def renovation_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора ремонта"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем вариант ремонта и object_id из callback_data
    # Формат: renovation_{option}_{object_id}
    callback_data = query.data
    parts = callback_data.split("_", 2)  # Разделяем на ["renovation", "{option}", "{object_id}"]
    
    if len(parts) < 3:
        await query.message.reply_text("Ошибка: неверный формат данных.")
        return ConversationHandler.END
    
    renovation = parts[1]  # Вариант ремонта
    object_id = parts[2]   # ID объекта
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    # Обновляем объект
    update_object(object_id, {"renovation": renovation})
    
    # Log action
    try:
        user_obj = get_user(str(user.id))
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_renovation_updated',
                details_json={'object_id': object_id, 'renovation': renovation},
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU
