"""
Publication handlers for bot
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, InputFile
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils import (
    get_user, get_object, update_object, get_districts_config, get_price_ranges,
    format_publication_text, get_moscow_time, format_moscow_datetime
)
from app.database import db
from bot.models import Object, ActionLog, Chat, PublicationHistory
from datetime import timedelta
from bot.handlers_object import user_data, show_object_preview_with_menu
from bot.handlers.object_edit import OBJECT_PREVIEW_MENU

logger = logging.getLogger(__name__)


def get_parse_mode_for_text(text: str):
    """Определить parse_mode для текста"""
    if "<" in text and ">" in text:
        return 'HTML'
    return None


async def get_target_chats_for_object(obj: Object) -> list:
    """Определить целевые чаты для объекта"""
    target_chats = []
    
    # Get all active bot chats
    chats = db.session.query(Chat).filter_by(owner_type='bot', is_active=True).all()
    
    rooms_type = obj.rooms_type or ""
    districts = obj.districts_json or []
    price = obj.price or 0
    
    districts_config = get_districts_config()
    
    # Add parent districts
    all_districts = set(districts)
    for district in districts:
        if isinstance(district, str) and district in districts_config:
            parent_districts = districts_config[district]
            if isinstance(parent_districts, list):
                all_districts.update(parent_districts)
    
    for chat in chats:
            matches = False
            filters = chat.filters_json or {}
            
            # Проверка типа привязки "общий" - такой чат получает все посты
            binding_type = filters.get('binding_type')
            if binding_type == 'common':
                if chat.chat_id not in target_chats:
                    target_chats.append(chat.chat_id)
                continue  # Пропускаем проверку фильтров для "общего" чата
            
            # Check if filters_json is used (has at least one filter)
            has_filters_json = bool(filters.get('rooms_types') or filters.get('districts') or 
                                   filters.get('price_min') is not None or filters.get('price_max') is not None)
            
            if has_filters_json:
                # Check all conditions - chat must match ALL specified filters
                rooms_match = True
                districts_match = True
                price_match = True
                
                # Check by rooms type
                if filters.get('rooms_types'):
                    rooms_match = rooms_type in filters['rooms_types']
                
                # Check by districts
                if filters.get('districts'):
                    chat_districts = set(filters['districts'])
                    districts_match = bool(chat_districts.intersection(all_districts))
                
                # Check by price range
                price_min = filters.get('price_min')
                price_max = filters.get('price_max')
                if price_min is not None or price_max is not None:
                    price_min = price_min or 0
                    price_max = price_max if price_max is not None else float('inf')
                    price_match = price_min <= price < price_max
                
                # Chat matches if all specified filters match
                if rooms_match and districts_match and price_match:
                    matches = True
            else:
                # Legacy category support
                category = chat.category or ""
                
                # Check by rooms type
                if category.startswith("rooms_") and category.replace("rooms_", "") == rooms_type:
                    matches = True
                
                # Check by district
                if category.startswith("district_"):
                    district_name = category.replace("district_", "")
                    if district_name in all_districts:
                        matches = True
                
                # Check by price range
                if category.startswith("price_"):
                    try:
                        # Format: price_4000_6000
                        parts = category.replace("price_", "").split("_")
                        if len(parts) == 2:
                            min_price = float(parts[0])
                            max_price = float(parts[1])
                            if min_price <= price < max_price:
                                matches = True
                    except:
                        pass
            
            if matches and chat.chat_id not in target_chats:
                target_chats.append(chat.chat_id)
    
    return target_chats


async def publish_immediate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Опубликовать сейчас'"""
    query = update.callback_query
    await query.answer()
    
    object_id = query.data.replace("publish_immediate_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    obj = get_object(object_id)
    if not obj:
        await query.answer("Ошибка: объект не найден.", show_alert=True)
        return OBJECT_PREVIEW_MENU
    
    user_obj = get_user(str(user.id))
    
    # Check contacts
    phone = obj.phone_number
    if not phone and user_obj:
        phone = user_obj.phone
    
    show_username = obj.show_username or False
    has_username = show_username and user_obj and user_obj.username
    
    if not phone and not has_username:
        warning_text = "⚠️ <b>Внимание!</b>\n\n"
        warning_text += "С вами не смогут связаться, так как не указан номер телефона и не включен ник Telegram.\n\n"
        warning_text += "Пожалуйста, укажите номер телефона для публикации."
        
        keyboard = [
            [InlineKeyboardButton("Указать номер телефона", callback_data=f"edit_contacts_{object_id}")],
            [InlineKeyboardButton("Назад к редактированию", callback_data="back_to_preview")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.reply_text(warning_text, reply_markup=reply_markup, parse_mode='HTML')
        except:
            await query.edit_message_text(warning_text, reply_markup=reply_markup, parse_mode='HTML')
                
                return OBJECT_PREVIEW_MENU
    
    # Get target chats
    target_chats = await get_target_chats_for_object(obj)
    
    # Get chat names
    chat_names = []
    chats = db.session.query(Chat).filter(Chat.chat_id.in_(target_chats)).all()
    for chat in chats:
        chat_names.append(chat.title or f'Чат {chat.chat_id}')
    
    # Format text with chat list
    if chat_names:
        chats_text = "Объявление будет опубликовано в следующие чаты:\n\n"
        for i, name in enumerate(chat_names, 1):
            chats_text += f"{i}. {name}\n"
    else:
        chats_text = "⚠️ Не найдены подходящие чаты для публикации.\n\n"
        chats_text += "Возможные причины:\n"
        chats_text += "• Чаты еще не настроены администратором\n"
        chats_text += "• Нет чатов, соответствующих параметрам объекта"
    
    # Confirmation buttons
    keyboard = []
    if chat_names:
        keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_publish_{object_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад к редактированию", callback_data="back_to_preview")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.message.reply_text(chats_text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        await query.edit_message_text(chats_text, reply_markup=reply_markup, parse_mode='HTML')
    
    return OBJECT_PREVIEW_MENU


async def confirm_publish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения публикации"""
    query = update.callback_query
    await query.answer("Публикация начата...")
    
    object_id = query.data.replace("confirm_publish_", "")
    
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {}
    user_data[user.id]["object_id"] = object_id
    
    try:
        # Publish immediately
        await publish_object_immediate(update, context, object_id)
        # Возвращаемся к меню превью, а не END, чтобы пользователь мог продолжить работу
        return OBJECT_PREVIEW_MENU
    except Exception as e:
        logger.error(f"Error in confirm_publish_handler: {e}", exc_info=True)
        await query.answer(f"Ошибка при публикации: {str(e)}", show_alert=True)
        return OBJECT_PREVIEW_MENU


async def publish_object_immediate(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: str):
    """Немедленная публикация объекта"""
    obj = get_object(object_id)
    if not obj:
        if update.callback_query:
            await update.callback_query.answer("Объект не найден.", show_alert=True)
        return
    
    user = update.effective_user
    user_obj = get_user(str(user.id))
    
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
    
    # Format publication text
    publication_text = format_publication_text(obj, user_obj, is_preview=False, publication_format=publication_format)
    
    # Get target chats
    target_chats = await get_target_chats_for_object(obj)
    
    if not target_chats:
        if update.callback_query:
            await update.callback_query.answer("Не найдены подходящие чаты для публикации.", show_alert=True)
        return
    
    # Get photos
    photos_json = obj.photos_json or []
    
    published_count = 0
    errors = []
    
    # Publish to each chat
    for chat_id in target_chats:
        try:
                chat = db.session.query(Chat).filter_by(chat_id=chat_id).first()
                if not chat:
                    continue
                
                telegram_chat_id = chat.telegram_chat_id
            
            # Send message - всегда отправляем фото если оно есть
            # Всегда используем путь к файлу на сервере
            if photos_json and len(photos_json) > 0:
                # Берем первое фото (только одно фото разрешено)
                photo_data = photos_json[0]
                
                # Извлекаем путь к файлу
                photo_path = None
                if isinstance(photo_data, dict):
                    # Если это объект - берем path
                    photo_path = photo_data.get('path', '')
                elif isinstance(photo_data, str):
                    # Если это строка - это путь к файлу
                    photo_path = photo_data
                
                # Загружаем файл с сервера и отправляем
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
                    
                    logger.info(f"Trying to send photo in publication: photo_path={photo_path}, full_path={full_path}, exists={os.path.exists(full_path)}")
                    if os.path.exists(full_path):
                        # Отправляем фото через InputFile для надежности
                            await context.bot.send_photo(
                                chat_id=telegram_chat_id,
                            photo=InputFile(full_path),
                                caption=publication_text,
                                parse_mode='HTML'
                            )
                    else:
                        logger.warning(f"Photo file not found: {full_path} (original: {photo_path})")
                        # Отправляем только текст если файл не найден
                        await context.bot.send_message(
                            chat_id=telegram_chat_id,
                            text=publication_text,
                            parse_mode='HTML'
                        )
                else:
                    # Если путь не найден - отправляем только текст
                    await context.bot.send_message(
                        chat_id=telegram_chat_id,
                        text=publication_text,
                        parse_mode='HTML'
                    )
            else:
                # Если фото нет - отправляем только текст
                await context.bot.send_message(
                    chat_id=telegram_chat_id,
                    text=publication_text,
                    parse_mode='HTML'
                )
            
            # Update chat statistics and create publication history
            chat = db.session.query(Chat).filter_by(chat_id=chat_id).first()
            if chat:
                chat.total_publications = (chat.total_publications or 0) + 1
                chat.last_publication = datetime.utcnow()
                
                # Create publication history entry
                history = PublicationHistory(
                    object_id=object_id,
                    chat_id=chat_id,
                    account_id=None,  # Bot publication
                    published_at=datetime.utcnow(),
                    message_id=None,  # Will be updated if needed
                    deleted=False
                )
                db.session.add(history)
                db.session.commit()
            
            published_count += 1
            
            # Rate limit: 20 messages per minute
            if published_count % 20 == 0:
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(3)  # 3 seconds between messages
            
        except Exception as e:
            logger.error(f"Error publishing to chat {chat_id}: {e}", exc_info=True)
            errors.append(str(e))
            continue
    
    # Update object status
    now = get_moscow_time()
    publication_datetime = format_moscow_datetime(now)
    update_object(object_id, {
        "status": "опубликовано",
        "publication_date": datetime.utcnow()
    })
    
    # Log action
    try:
        if user_obj:
            action_log = ActionLog(
                user_id=user_obj.user_id,
                action='bot_object_published',
                details_json={
                    'object_id': object_id,
                    'chats_count': len(target_chats),
                    'published_count': published_count,
                    'errors': errors
                },
                created_at=datetime.utcnow()
            )
            db.session.add(action_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    # Send notification to user and show preview again
    if update.callback_query:
        if published_count > 0:
            notification_text = f"✅ <b>Объект успешно опубликован!</b>\n\n"
            notification_text += f"📊 Опубликовано в {published_count} из {len(target_chats)} чатов\n"
            if errors:
                notification_text += f"⚠️ Ошибок: {len(errors)}\n"
            notification_text += f"📅 {publication_datetime}"
            
            await update.callback_query.message.reply_text(notification_text, parse_mode='HTML')
            # Показываем превью объекта снова после публикации
            await show_object_preview_with_menu(update, context, object_id)
        else:
            await update.callback_query.answer("Ошибка: не удалось опубликовать объект.", show_alert=True)
            # Показываем превью объекта даже при ошибке
            await show_object_preview_with_menu(update, context, object_id)

