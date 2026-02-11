"""
Object creation handlers for bot
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.utils import (
    get_user, update_user_activity, create_object, get_object, update_object,
    get_user_id_prefix, set_user_id_prefix, generate_next_id_prefix,
    format_publication_text, get_rooms_config, get_districts_config
)
from bot.database import get_db
from bot.models import Object, SystemSetting, ActionLog
from bot.config import ROLE_START, ROLE_BROKE, ROLE_BEGINNER
from datetime import datetime

logger = logging.getLogger(__name__)

# Conversation states
OBJECT_WAITING_ROOMS = 1
OBJECT_WAITING_DISTRICT = 2
OBJECT_WAITING_PRICE = 3
OBJECT_WAITING_AREA = 4
OBJECT_WAITING_FLOOR = 5
OBJECT_WAITING_COMMENT = 6
OBJECT_WAITING_MEDIA = 7
OBJECT_WAITING_RENOVATION = 8
OBJECT_WAITING_ADDRESS = 9
OBJECT_WAITING_CONTACTS = 10

# User data storage (in-memory, should be moved to Redis in production)
user_data = {}




async def add_object_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start object creation process"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_id_str = str(user.id)
    
    # Clear old user data if exists
    if user.id in user_data:
        old_object_id = user_data[user.id].get("object_id")
        if old_object_id:
            try:
                obj = get_object(old_object_id)
                if obj:
                    db_session = get_db()
                    try:
                        db_session.delete(obj)
                        db_session.commit()
                    finally:
                        db_session.close()
            except Exception as e:
                logger.error(f"Error deleting old object: {e}")
        user_data.pop(user.id, None)
    
    # Create new object
    try:
        object_id = create_object(user_id_str)
        
        # Initialize user data
        user_data[user.id] = {
            "object_id": object_id,
            "districts": []
        }
        
        # Update user role if needed
        user_obj = get_user(user_id_str)
        if user_obj:
            if user_obj.bot_role in [ROLE_START, ROLE_BROKE]:
                user_obj.bot_role = ROLE_BEGINNER
                db_session = get_db()
                try:
                    db_session.commit()
                finally:
                    db_session.close()
        
        # Log action
        try:
            db_session = get_db()
            try:
                if user_obj:
                    action_log = ActionLog(
                        user_id=user_obj.user_id,
                        action='bot_object_creation_started',
                        details_json={'object_id': object_id},
                        created_at=datetime.utcnow()
                    )
                    db_session.add(action_log)
                    db_session.commit()
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
        
        # Step 1: Select rooms type
        rooms = get_rooms_config()
        keyboard = []
        row = []
        for i, room in enumerate(rooms):
            row.append(InlineKeyboardButton(room, callback_data=f"rooms_{room}"))
            if len(row) == 3 or i == len(rooms) - 1:
                keyboard.append(row)
                row = []
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏠 <b>Создание объекта</b>\n\nВыберите тип комнат:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return OBJECT_WAITING_ROOMS
        
    except Exception as e:
        logger.error(f"Error in add_object_start: {e}", exc_info=True)
        await query.edit_message_text(f"Ошибка при создании объекта: {str(e)}")
        return ConversationHandler.END


async def object_rooms_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rooms type selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id not in user_data:
        await query.edit_message_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    rooms_type = query.data.replace("rooms_", "")
    object_id = user_data[user.id]["object_id"]
    
    # Update object
    db_session = get_db()
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        if obj:
            obj.rooms_type = rooms_type
            db_session.commit()
    finally:
        db_session.close()
    
    # Step 2: Select districts
    districts_config = get_districts_config()
    districts = list(districts_config.keys()) if districts_config else []
    
    if not districts:
        # Skip districts, go to price
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "💰 Введите цену в тысячах рублей:",
            reply_markup=reply_markup
        )
        return OBJECT_WAITING_PRICE
    
    # Show districts selection
    keyboard = [[InlineKeyboardButton(district, callback_data=f"district_{district}")] 
                for district in districts]
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📍 Выберите район:",
        reply_markup=reply_markup
    )
    return OBJECT_WAITING_DISTRICT


async def object_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle district selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id not in user_data:
        await query.edit_message_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    district = query.data.replace("district_", "")
    
    # Add district
    if "districts" not in user_data[user.id]:
        user_data[user.id]["districts"] = []
    if district not in user_data[user.id]["districts"]:
        user_data[user.id]["districts"].append(district)
    
    # Update object
    object_id = user_data[user.id]["object_id"]
    db_session = get_db()
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        if obj:
            obj.districts_json = user_data[user.id]["districts"]
            db_session.commit()
    finally:
        db_session.close()
    
    # Go to price
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "💰 Введите цену в тысячах рублей:",
        reply_markup=reply_markup
    )
    return OBJECT_WAITING_PRICE


async def object_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle price input"""
    user = update.effective_user
    if user.id not in user_data:
        await update.message.reply_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    try:
        price = float(update.message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
        
        # Update object
        object_id = user_data[user.id]["object_id"]
        db_session = get_db()
        try:
            obj = db_session.query(Object).filter_by(object_id=object_id).first()
            if obj:
                obj.price = price
                db_session.commit()
        finally:
            db_session.close()
        
        # Go to area
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📐 Введите площадь в м²:",
            reply_markup=reply_markup
        )
        return OBJECT_WAITING_AREA
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат цены. Введите число больше нуля:")
        return OBJECT_WAITING_PRICE


async def object_area_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle area input"""
    user = update.effective_user
    if user.id not in user_data:
        await update.message.reply_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    try:
        area = float(update.message.text.replace(",", "."))
        if area <= 0:
            raise ValueError
        
        # Update object
        object_id = user_data[user.id]["object_id"]
        db_session = get_db()
        rooms_type = None
        comment = None
        try:
            obj = db_session.query(Object).filter_by(object_id=object_id).first()
            if obj:
                # Get rooms_type and comment before closing session
                rooms_type = obj.rooms_type
                comment = obj.comment
                obj.area = area
                db_session.commit()
        finally:
            db_session.close()
        
        # If comment exists, this is editing from menu - return to preview
        if comment:
            from bot.handlers_object_edit import OBJECT_PREVIEW_MENU
            await show_object_preview_with_menu(update, context, object_id)
            return OBJECT_PREVIEW_MENU
        
        # Check if rooms_type is "Дом" - skip floor
        if rooms_type == "Дом":
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📝 Введите описание (комментарий):",
                reply_markup=reply_markup
            )
            return OBJECT_WAITING_COMMENT
        
        # Go to floor
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🏢 Введите этаж (например: 5/9):",
            reply_markup=reply_markup
        )
        return OBJECT_WAITING_FLOOR
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат площади. Введите число больше нуля:")
        return OBJECT_WAITING_AREA


async def object_floor_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle floor input"""
    user = update.effective_user
    if user.id not in user_data:
        await update.message.reply_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    floor = update.message.text.strip()
    
    # Update object
    object_id = user_data[user.id]["object_id"]
    db_session = get_db()
    comment = None
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        if obj:
            comment = obj.comment
            obj.floor = floor
            db_session.commit()
    finally:
        db_session.close()
    
    # If comment exists, this is editing from menu - return to preview
    if comment:
        from bot.handlers_object_edit import OBJECT_PREVIEW_MENU
        await show_object_preview_with_menu(update, context, object_id)
        return OBJECT_PREVIEW_MENU
    
    # Go to comment
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📝 Введите описание (комментарий):",
        reply_markup=reply_markup
    )
    return OBJECT_WAITING_COMMENT


async def object_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle comment input"""
    user = update.effective_user
    if user.id not in user_data:
        await update.message.reply_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    comment = update.message.text.strip()
    
    # Update object
    object_id = user_data[user.id]["object_id"]
    db_session = get_db()
    photos_count = 0
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        if obj:
            obj.comment = comment
            photos_count = len(obj.photos_json) if obj.photos_json else 0
            db_session.commit()
    finally:
        db_session.close()
    
    # If photos exist, this is editing from menu - return to preview
    if photos_count > 0:
        from bot.handlers_object_edit import OBJECT_PREVIEW_MENU
        await show_object_preview_with_menu(update, context, object_id)
        return OBJECT_PREVIEW_MENU
    
    # Go to media
    keyboard = [[InlineKeyboardButton("Пропустить", callback_data="skip_media")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📷 Отправьте фото объекта (до 10 фото). Нажмите 'Пропустить' если фото нет:",
        reply_markup=reply_markup
    )
    return OBJECT_WAITING_MEDIA


async def object_media_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media (photo) input"""
    user = update.effective_user
    if user.id not in user_data:
        await update.message.reply_text("Ошибка: сессия истекла. Начните заново.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    db_session = get_db()
    photos_json = []
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        
        if not obj:
            await update.message.reply_text("Ошибка: объект не найден.")
            return ConversationHandler.END
        
        # Get photos
        if update.message.photo:
            photos = update.message.photo
            # Get largest photo
            photo = photos[-1]
            
            # Save photo info (in production, download and save to uploads/)
            # For now, just store file_id
            photos_json = obj.photos_json or []
            if len(photos_json) < 10:
                photos_json.append({
                    'file_id': photo.file_id,
                    'file_unique_id': photo.file_unique_id
                })
                obj.photos_json = photos_json
                db_session.commit()
    finally:
        db_session.close()
    
    # Handle photo response (outside of db session)
    if update.message.photo:
        remaining = 10 - len(photos_json)
        if remaining > 0:
            await update.message.reply_text(
                f"✅ Фото добавлено. Осталось мест: {remaining}. Отправьте еще фото или нажмите 'Пропустить':"
            )
            return OBJECT_WAITING_MEDIA
        else:
            await update.message.reply_text("✅ Все фото добавлены (максимум 10).")
            # Check if this is editing (comment exists) or creation
            obj = get_object(object_id)
            if obj and obj.comment:
                from bot.handlers_object_edit import OBJECT_PREVIEW_MENU
                await show_object_preview_with_menu(update, context, object_id)
                return OBJECT_PREVIEW_MENU
            return await finish_object_creation(update, context)
    
    await update.message.reply_text("❌ Отправьте фото или нажмите 'Пропустить'.")
    return OBJECT_WAITING_MEDIA


async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip media step"""
    query = update.callback_query
    await query.answer()
    return await finish_object_creation(update, context)


async def show_object_preview_with_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: str = None):
    """Показать предпросмотр объекта с меню редактирования"""
    user = update.effective_user
    user_id_str = str(user.id)
    
    # Get object_id from user_data if not provided
    if not object_id:
        if user.id not in user_data:
            if update.callback_query:
                await update.callback_query.edit_message_text("Ошибка: сессия истекла.")
            else:
                await update.message.reply_text("Ошибка: сессия истекла.")
            return ConversationHandler.END
        object_id = user_data[user.id]["object_id"]
    
    # Get object and user
    db_session = get_db()
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        user_obj = get_user(user_id_str)
        
        if not obj:
            if update.callback_query:
                await update.callback_query.edit_message_text("Ошибка: объект не найден.")
            else:
                await update.message.reply_text("Ошибка: объект не найден.")
            return ConversationHandler.END
        
        # Получаем формат публикации из конфигурации автопубликации
        publication_format = 'default'
        try:
            from app.database import db as web_db
            from app.models.autopublish_config import AutopublishConfig
            web_cfg = web_db.session.query(AutopublishConfig).filter_by(
                object_id=object_id
            ).first()
            if web_cfg and web_cfg.accounts_config_json:
                accounts_cfg = web_cfg.accounts_config_json
                if isinstance(accounts_cfg, dict):
                    publication_format = accounts_cfg.get('publication_format', 'default')
        except Exception:
            # Если не удалось получить конфигурацию, используем формат по умолчанию
            pass
        
        # Format text
        text = format_publication_text(obj, user_obj, is_preview=True, publication_format=publication_format)
        
        # Add media count
        photos_count = len(obj.photos_json) if obj.photos_json else 0
        if photos_count > 0:
            text += f"\n<b>Медиа:</b> {photos_count} файл(ов)\n"
        
        # Create menu keyboard
        keyboard = [
            [InlineKeyboardButton("Изменить стоимость", callback_data=f"edit_price_{object_id}")],
            [InlineKeyboardButton("Выбрать фото", callback_data=f"add_media_{object_id}")],
            [InlineKeyboardButton("Изменить комментарий", callback_data=f"edit_comment_{object_id}")],
            [
                InlineKeyboardButton("Добавить еще район", callback_data=f"add_district_{object_id}"),
                InlineKeyboardButton("Изменить район", callback_data=f"edit_district_{object_id}")
            ],
            [
                InlineKeyboardButton("Площадь", callback_data=f"edit_area_{object_id}"),
                InlineKeyboardButton("Этаж", callback_data=f"edit_floor_{object_id}")
            ],
            [
                InlineKeyboardButton("Изменить комнаты", callback_data=f"edit_rooms_{object_id}"),
                InlineKeyboardButton("Состояние ремонта", callback_data=f"edit_renovation_{object_id}")
            ],
            [
                InlineKeyboardButton("Адрес", callback_data=f"edit_address_{object_id}"),
                InlineKeyboardButton("Контакты", callback_data=f"edit_contacts_{object_id}")
            ],
            [InlineKeyboardButton("Опубликовать сейчас", callback_data=f"publish_immediate_{object_id}")],
            [InlineKeyboardButton("Автопубликация", callback_data=f"toggle_autopublish_{object_id}")],
            [
                InlineKeyboardButton("Удалить", callback_data=f"delete_object_{object_id}"),
                InlineKeyboardButton("Мои объекты", callback_data="my_objects")
            ],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Determine message source
        if update.message:
            message = update.message
        elif update.callback_query:
            message = update.callback_query.message
        else:
            return ConversationHandler.END
        
        # Send media if exists
        photos_json = obj.photos_json or []
        preview_message = None
        
        if photos_json:
            try:
                media_group = []
                for photo_data in photos_json[:10]:
                    if isinstance(photo_data, dict):
                        file_id = photo_data.get('file_id')
                        if file_id:
                            media_group.append(InputMediaPhoto(
                                file_id,
                                caption=text if len(media_group) == 0 else None
                            ))
                
                if len(media_group) == 1:
                    preview_message = await message.reply_photo(
                        photo=media_group[0].media,
                        caption=text,
                        parse_mode='HTML'
                    )
                elif len(media_group) > 1:
                    # Update first media with HTML parse mode
                    if media_group[0].caption:
                        media_group[0].parse_mode = 'HTML'
                    sent_messages = await message.reply_media_group(media=media_group)
                    if sent_messages:
                        preview_message = sent_messages[0]
                else:
                    preview_message = await message.reply_text(text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending media: {e}")
                preview_message = await message.reply_text(text, parse_mode='HTML')
        else:
            preview_message = await message.reply_text(text, parse_mode='HTML')
        
        # Send menu
        menu_text = "Выберите действие:"
        menu_message = await message.reply_text(menu_text, reply_markup=reply_markup)
        
        # Store message IDs for later deletion if needed
        if user.id not in user_data:
            user_data[user.id] = {}
        user_data[user.id]["preview_message_id"] = preview_message.message_id
        user_data[user.id]["menu_message_id"] = menu_message.message_id
        user_data[user.id]["preview_chat_id"] = message.chat_id
        
    finally:
        db_session.close()
    
    # Return preview menu state instead of END to allow editing
    from bot.handlers_object_edit import OBJECT_PREVIEW_MENU
    return OBJECT_PREVIEW_MENU


async def finish_object_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish object creation and show editing menu"""
    user = update.effective_user
    if user.id not in user_data:
        if update.callback_query:
            await update.callback_query.edit_message_text("Ошибка: сессия истекла.")
        else:
            await update.message.reply_text("Ошибка: сессия истекла.")
        return ConversationHandler.END
    
    object_id = user_data[user.id]["object_id"]
    db_session = get_db()
    try:
        obj = db_session.query(Object).filter_by(object_id=object_id).first()
        
        if not obj:
            if update.callback_query:
                await update.callback_query.edit_message_text("Ошибка: объект не найден.")
            else:
                await update.message.reply_text("Ошибка: объект не найден.")
            return ConversationHandler.END
        
        # Mark as draft
        obj.status = 'черновик'
        db_session.commit()
    finally:
        db_session.close()
    
    # Show preview with menu (don't clear user_data - keep object_id for editing)
    return await show_object_preview_with_menu(update, context, object_id)


async def cancel_object_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel object creation"""
    user = update.effective_user
    if user.id in user_data:
        object_id = user_data[user.id].get("object_id")
        if object_id:
            try:
                obj = get_object(object_id)
                if obj:
                    db_session = get_db()
                    try:
                        db_session.delete(obj)
                        db_session.commit()
                    finally:
                        db_session.close()
            except Exception as e:
                logger.error(f"Error deleting object: {e}")
        user_data.pop(user.id, None)
    
    await update.message.reply_text("❌ Создание объекта отменено.")
    return ConversationHandler.END


# Create conversation handler
def create_object_conversation_handler():
    """Create conversation handler for object creation"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(add_object_start, pattern="^add_object$")],
        states={
            OBJECT_WAITING_ROOMS: [CallbackQueryHandler(object_rooms_selected, pattern="^rooms_")],
            OBJECT_WAITING_DISTRICT: [CallbackQueryHandler(object_district_selected, pattern="^district_")],
            OBJECT_WAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, object_price_input)],
            OBJECT_WAITING_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, object_area_input)],
            OBJECT_WAITING_FLOOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, object_floor_input)],
            OBJECT_WAITING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, object_comment_input)],
            OBJECT_WAITING_MEDIA: [
                MessageHandler(filters.PHOTO, object_media_received),
                CallbackQueryHandler(skip_media, pattern="^skip_media$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_object_creation, pattern="^back_to_menu$"),
            MessageHandler(filters.COMMAND, cancel_object_creation)
        ],
        name="add_object_handler"
    )

