"""
Publication handlers for bot
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils import (
    get_user, get_object, update_object, get_districts_config, get_price_ranges,
    format_publication_text, get_moscow_time, format_moscow_datetime
)
from bot.database import get_db
from bot.models import Object, ActionLog, Chat, PublicationHistory
from datetime import timedelta
from bot.handlers_object import user_data, show_object_preview_with_menu
from bot.handlers_object_edit import OBJECT_PREVIEW_MENU

logger = logging.getLogger(__name__)


def get_parse_mode_for_text(text: str):
    """Определить parse_mode для текста"""
    if "<" in text and ">" in text:
        return 'HTML'
    return None


async def get_target_chats_for_object(obj: Object) -> list:
    """Определить целевые чаты для объекта"""
    target_chats = []
    
    db = get_db()
    try:
        # Get all active bot chats
        chats = db.query(Chat).filter_by(owner_type='bot', is_active=True).all()
        
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
    finally:
        db.close()


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
    
    # Check if object was already published within last 24 hours
    # Проверка не применяется для админов (они могут публиковать без ограничений)
    user_obj = get_user(str(user.id))
    is_admin = user_obj and user_obj.web_role == 'admin'
    
    if not is_admin:
        db = get_db()
        try:
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_publications = db.query(PublicationHistory).filter(
                PublicationHistory.object_id == object_id,
                PublicationHistory.published_at >= yesterday,
                PublicationHistory.deleted == False
            ).all()
            
            if recent_publications:
                blocked_chats = []
                for pub in recent_publications:
                    chat = db.query(Chat).filter_by(chat_id=pub.chat_id).first()
                    if chat:
                        blocked_chats.append(chat.title or f'Чат {chat.chat_id}')
                
                if blocked_chats:
                    error_text = "⚠️ <b>Ошибка!</b>\n\n"
                    error_text += "Этот объект уже был опубликован в следующие чаты в течение последних 24 часов:\n\n"
                    for i, name in enumerate(blocked_chats, 1):
                        error_text += f"{i}. {name}\n"
                    error_text += "\nОдин объект не может быть опубликован в один и тот же чат чаще чем раз в сутки."
                    
                    keyboard = [[InlineKeyboardButton("⬅️ Назад к редактированию", callback_data="back_to_preview")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        await query.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
                    except:
                        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')
                    
                    return OBJECT_PREVIEW_MENU
        finally:
            db.close()
    
    # Get target chats
    target_chats = await get_target_chats_for_object(obj)
    
    # Get chat names
    db = get_db()
    chat_names = []
    try:
        chats = db.query(Chat).filter(Chat.chat_id.in_(target_chats)).all()
        for chat in chats:
            chat_names.append(chat.title or f'Чат {chat.chat_id}')
    finally:
        db.close()
    
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
        return ConversationHandler.END
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
                # Check if object was published to this chat within last 24 hours
                # Проверка не применяется для админов (они могут публиковать без ограничений)
                user_obj = get_user(str(user.id))
                is_admin = user_obj and user_obj.web_role == 'admin'
                
                if not is_admin:
                    db = get_db()
                    try:
                        chat = db.query(Chat).filter_by(chat_id=chat_id).first()
                        if not chat:
                            continue
                        
                        # Check publication history for this object and chat
                        yesterday = datetime.utcnow() - timedelta(days=1)
                        recent_publication = db.query(PublicationHistory).filter(
                            PublicationHistory.object_id == object_id,
                            PublicationHistory.chat_id == chat_id,
                            PublicationHistory.published_at >= yesterday,
                            PublicationHistory.deleted == False
                        ).first()
                        
                        if recent_publication:
                            logger.info(f"Object {object_id} was already published to chat {chat_id} within 24 hours, skipping")
                            continue
                        
                        telegram_chat_id = chat.telegram_chat_id
                    finally:
                        db.close()
                else:
                    # Для админов просто получаем telegram_chat_id без проверки
                    db = get_db()
                    try:
                        chat = db.query(Chat).filter_by(chat_id=chat_id).first()
                        if not chat:
                            continue
                        telegram_chat_id = chat.telegram_chat_id
                    finally:
                        db.close()
            
            # Send message
            if photos_json:
                # Send with media
                media_group = []
                for photo_data in photos_json[:10]:
                    if isinstance(photo_data, dict):
                        file_id = photo_data.get('file_id')
                        if file_id:
                            media_group.append(InputMediaPhoto(
                                file_id,
                                caption=publication_text if len(media_group) == 0 else None,
                                parse_mode='HTML' if len(media_group) == 0 else None
                            ))
                
                if len(media_group) == 1:
                    await context.bot.send_photo(
                        chat_id=telegram_chat_id,
                        photo=media_group[0].media,
                        caption=publication_text,
                        parse_mode='HTML'
                    )
                elif len(media_group) > 1:
                    await context.bot.send_media_group(
                        chat_id=telegram_chat_id,
                        media=media_group
                    )
                else:
                    await context.bot.send_message(
                        chat_id=telegram_chat_id,
                        text=publication_text,
                        parse_mode='HTML'
                    )
            else:
                # Send text only
                await context.bot.send_message(
                    chat_id=telegram_chat_id,
                    text=publication_text,
                    parse_mode='HTML'
                )
            
            # Update chat statistics and create publication history
            db = get_db()
            try:
                chat = db.query(Chat).filter_by(chat_id=chat_id).first()
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
                    db.add(history)
                    db.commit()
            finally:
                db.close()
            
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
        db = get_db()
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
                db.add(action_log)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    # Send notification to user
    if update.callback_query:
        if published_count > 0:
            notification_text = f"✅ <b>Объект успешно опубликован!</b>\n\n"
            notification_text += f"📊 Опубликовано в {published_count} из {len(target_chats)} чатов\n"
            if errors:
                notification_text += f"⚠️ Ошибок: {len(errors)}\n"
            notification_text += f"📅 {publication_datetime}"
            
            await update.callback_query.message.reply_text(notification_text, parse_mode='HTML')
        else:
            await update.callback_query.answer("Ошибка: не удалось опубликовать объект.", show_alert=True)

