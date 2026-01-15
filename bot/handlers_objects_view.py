"""
Object viewing handlers for bot
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.utils import get_user, get_user_objects
from bot.database import get_db
from bot.models import Object, ActionLog
from datetime import datetime

logger = logging.getLogger(__name__)


async def my_objects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's objects list"""
    user = update.effective_user
    user_id_str = str(user.id)
    
    # Get user from DB
    user_obj = get_user(user_id_str)
    if not user_obj:
        await update.message.reply_text("Ошибка: пользователь не найден.")
        return
    
    # Get objects
    objects = get_user_objects(user_id_str)
    
    if not objects:
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 У вас пока нет объектов.\n\nСоздайте первый объект через меню!",
            reply_markup=reply_markup
        )
        return
    
    # Sort by creation date (newest first)
    objects.sort(key=lambda x: x.creation_date if x.creation_date else datetime.min, reverse=True)
    
    # Show first 10 objects
    text = f"📋 <b>Мои объекты</b> (всего: {len(objects)})\n\n"
    
    for i, obj in enumerate(objects[:10], 1):
        text += f"<b>{i}. {obj.object_id}</b>\n"
        if obj.rooms_type:
            text += f"   Тип: {obj.rooms_type}\n"
        if obj.price > 0:
            text += f"   Цена: {obj.price} тыс. руб.\n"
        if obj.area:
            text += f"   Площадь: {obj.area} м²\n"
        if obj.districts_json:
            text += f"   Районы: {', '.join(obj.districts_json)}\n"
        text += f"   Статус: {obj.status}\n\n"
    
    if len(objects) > 10:
        text += f"\n<i>Показано 10 из {len(objects)} объектов</i>"
    
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # Log action
    try:
        db = get_db()
        try:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_my_objects_viewed',
                details_json={'objects_count': len(objects)},
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
    
    # Create fake message update
    class FakeMessage:
        def __init__(self, query):
            self.reply_text = query.edit_message_text
            self.from_user = query.from_user
    
    fake_update = Update(
        update_id=update.update_id,
        message=FakeMessage(query)
    )
    fake_update.effective_user = update.effective_user
    
    await my_objects_command(fake_update, context)

