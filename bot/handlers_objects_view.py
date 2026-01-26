"""
Object viewing handlers for bot
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.utils import get_user, get_user_objects, get_object
from bot.database import get_db
from bot.models import Object, ActionLog
from bot.handlers_object import user_data
from datetime import datetime

logger = logging.getLogger(__name__)


async def my_objects_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Show user's objects list with buttons"""
    user = update.effective_user
    user_id_str = str(user.id)
    
    # Get user from DB
    user_obj = get_user(user_id_str)
    if not user_obj:
        if update.message:
            await update.message.reply_text("Ошибка: пользователь не найден.")
        elif update.callback_query:
            await update.callback_query.answer("Ошибка: пользователь не найден.", show_alert=True)
        return
    
    # Get objects
    objects = get_user_objects(user_id_str)
    
    if not objects:
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📋 У вас пока нет объектов.\n\nСоздайте первый объект через меню!"
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    # Sort by creation date (newest first)
    objects.sort(key=lambda x: x.creation_date if x.creation_date else datetime.min, reverse=True)
    
    # Pagination: show 10 objects per page
    objects_per_page = 10
    total_pages = (len(objects) + objects_per_page - 1) // objects_per_page
    start_idx = page * objects_per_page
    end_idx = min(start_idx + objects_per_page, len(objects))
    page_objects = objects[start_idx:end_idx]
    
    # Format text
    text = f"📋 <b>Мои объекты</b>\n\n"
    text += f"Количество объектов: <b>{len(objects)}</b>\n\n"
    
    # Create keyboard with buttons for each object
    keyboard = []
    
    for obj in page_objects:
        price = obj.price or 0
        rooms = obj.rooms_type or ""
        districts = obj.districts_json or []
        
        # Format button text: "3500 | 1к | Прикубанский | ABC123"
        button_text = f"{int(price)}"
        if rooms:
            button_text += f" | {rooms}"
        if districts:
            button_text += f" | {districts[0]}"
        button_text += f" | {obj.object_id}"
        
        # Add row with object button only
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_object_from_list_{obj.object_id}")])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"my_objects_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"my_objects_page_{page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # Log action
    try:
        db = get_db()
        try:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_my_objects_viewed',
                details_json={'objects_count': len(objects), 'page': page},
                created_at=datetime.utcnow()
            )
            db.add(action_log)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")


async def my_objects_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle my_objects callback"""
    query = update.callback_query
    await query.answer()
    
    # Check if this is pagination or object selection
    if query.data.startswith("my_objects_page_"):
        page = int(query.data.replace("my_objects_page_", ""))
        await my_objects_command(update, context, page)
    elif query.data.startswith("edit_object_from_list_"):
        # Handle object selection - open editing
        await edit_object_from_list(update, context)
    else:
        # Regular my_objects callback
        await my_objects_command(update, context, 0)


async def edit_object_from_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing object from list"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    object_id = query.data.replace("edit_object_from_list_", "")
    
    # Check if object exists and belongs to user
    obj = get_object(object_id)
    if not obj:
        await query.answer("Объект не найден.", show_alert=True)
        from telegram.ext import ConversationHandler
        return ConversationHandler.END
    
    user_obj = get_user(str(user.id))
    if not user_obj or obj.user_id != user_obj.user_id:
        await query.answer("Этот объект вам не принадлежит.", show_alert=True)
        from telegram.ext import ConversationHandler
        return ConversationHandler.END
    
    # Initialize user_data for editing
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    user_data[user.id]["districts"] = obj.districts_json or []
    
    # Show preview with menu
    from bot.handlers_object import show_object_preview_with_menu
    from bot.handlers_object_edit import OBJECT_PREVIEW_MENU
    await show_object_preview_with_menu(update, context, object_id)
    return OBJECT_PREVIEW_MENU

