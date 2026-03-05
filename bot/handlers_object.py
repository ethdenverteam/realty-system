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
from app.database import db
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
                    db.session.delete(obj)
                    db.session.commit()
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
                db.session.commit()
        
        # Log action
        try:
            if user_obj:
                action_log = ActionLog(
                    user_id=user_obj.user_id,
                    action='bot_object_creation_started',
                    details_json={'object_id': object_id},
                    created_at=datetime.utcnow()
                )
                db.session.add(action_log)
                db.session.commit()
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
                db.session.commit()
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
                db.session.commit()
        finally:
            db_session.close()
        
        # If comment exists, this is editing from menu - return to preview
        if comment:
            from bot.handlers.object_edit import OBJECT_PREVIEW_MENU
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
        from bot.handlers.object_edit import OBJECT_PREVIEW_MENU
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
        from bot.handlers.object_edit import OBJECT_PREVIEW_MENU
        await show_object_preview_with_menu(update, context, object_id)
        return OBJECT_PREVIEW_MENU
    
    # Go to media
    keyboard = [[InlineKeyboardButton("Пропустить", callback_data="skip_media")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📷 Отправьте одно фото объекта. Нажмите 'Пропустить' если фото нет:",
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
            
            # Download photo file from Telegram and save to disk
            # Always save to server - this is the only way we store photos
            photo_path = None
            try:
                # Get file info from Telegram
                file = await context.bot.get_file(photo.file_id)
                
                # Generate unique filename
                import os
                from datetime import datetime
                
                # Get UPLOAD_FOLDER - try app.config first, fallback to default
                try:
                    from app.config import Config
                    upload_folder = Config.UPLOAD_FOLDER
                except (ImportError, AttributeError):
                    # Fallback to default path
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    upload_folder = os.path.join(base_dir, 'static', 'uploads')
                
                # Get file extension from file_path or use .jpg as default
                file_ext = '.jpg'
                if file.file_path:
                    _, ext = os.path.splitext(file.file_path)
                    if ext:
                        file_ext = ext
                
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"{timestamp}_bot_photo{file_ext}"
                
                # Save to uploads folder
                filepath = os.path.join(upload_folder, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Download and save file
                await file.download_to_drive(filepath)
                
                # Store relative path - always use path, never file_id
                photo_path = f"uploads/{filename}"
            except Exception as e:
                logger.error(f"Error downloading photo from Telegram: {e}", exc_info=True)
                await update.message.reply_text("❌ Ошибка при сохранении фото. Попробуйте еще раз.")
                return OBJECT_WAITING_MEDIA
            
            # Save photo info - только одно фото разрешено
            # Always store only path to file on server
            if photo_path:
                photos_json = [photo_path]
            else:
                photos_json = []
            obj.photos_json = photos_json
            db_session.commit()
    finally:
        db_session.close()
    
    # Handle photo response (outside of db session)
    if update.message.photo:
        await update.message.reply_text("✅ Фото добавлено.")
        # Check if this is editing (comment exists) or creation
        obj = get_object(object_id)
        if obj and obj.comment:
            from bot.handlers.object_edit import OBJECT_PREVIEW_MENU
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
            [InlineKeyboardButton("Указать ЖК", callback_data=f"edit_residential_complex_{object_id}")],
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
        
        # Send media if exists - всегда отправляем фото если оно есть
        photos_json = obj.photos_json or []
        preview_message = None
        
        if photos_json and len(photos_json) > 0:
            try:
                # Берем первое фото (только одно фото разрешено)
                photo_data = photos_json[0]
                photo_file = None
                
                # Извлекаем путь к файлу - всегда используем путь к файлу на сервере
                photo_path = None
                if isinstance(photo_data, dict):
                    # Если это объект - берем path
                    photo_path = photo_data.get('path', '')
                elif isinstance(photo_data, str):
                    # Если это строка - это путь к файлу
                    photo_path = photo_data
                
                # Если есть путь к файлу, загружаем и отправляем
                if photo_path:
                    import os
                    
                    # Используем Config.UPLOAD_FOLDER напрямую
                    try:
                        from app.config import Config
                        upload_folder = Config.UPLOAD_FOLDER
                    except (ImportError, AttributeError):
                        # Fallback to default path
                        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                        upload_folder = os.path.join(base_dir, 'static', 'uploads')
                    
                    # photo_path может быть "uploads/filename.jpg" или просто "filename.jpg"
                    if photo_path.startswith('uploads/'):
                        # Убираем префикс "uploads/" и используем upload_folder
                        filename = photo_path.replace('uploads/', '', 1)
                        full_path = os.path.join(upload_folder, filename)
                    elif photo_path.startswith('/'):
                        # Абсолютный путь
                        full_path = photo_path
                    else:
                        # Относительный путь - используем upload_folder
                        full_path = os.path.join(upload_folder, photo_path)
                    
                    logger.info(f"Trying to send photo in preview: photo_path={photo_path}, full_path={full_path}, exists={os.path.exists(full_path)}")
                    if os.path.exists(full_path):
                        # Открываем файл и отправляем
                        with open(full_path, 'rb') as f:
                            preview_message = await message.reply_photo(
                                photo=f,
                                caption=text,
                                parse_mode='HTML'
                            )
                    else:
                        logger.warning(f"Photo file not found: {full_path} (original: {photo_path})")
                        preview_message = await message.reply_text(text, parse_mode='HTML')
                else:
                    # Если не удалось определить фото - отправляем только текст
                    preview_message = await message.reply_text(text, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending media: {e}", exc_info=True)
                preview_message = await message.reply_text(text, parse_mode='HTML')
        else:
            # Если фото нет - отправляем только текст
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
    from bot.handlers.object_edit import OBJECT_PREVIEW_MENU
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
                    try:
                        db.session.delete(obj)
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error deleting object from database: {e}")
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

