"""
Bot handlers - основные обработчики команд
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_user, update_user_activity, generate_web_code
from bot.config import ADMIN_ID
from bot.database import get_db
from bot.models import ActionLog

logger = logging.getLogger('bot.handlers')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    import sys
    user = update.effective_user
    logger.info(f"Received /start command from user {user.id} (@{user.username})")
    sys.stdout.flush()
    
    try:
        # Update user activity
        update_user_activity(str(user.id), user.username)
        
        # Check if start parameter is 'getcode'
        if context.args and len(context.args) > 0 and context.args[0] == 'getcode':
            # If start parameter is 'getcode', directly call getcode_command
            logger.info(f"Start parameter 'getcode' detected for user {user.id}")
            await getcode_command(update, context)
        else:
            # Show main menu
            await show_main_menu(update, context)
        logger.info(f"Successfully processed /start for user {user.id}")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"Error in start_command for user {user.id}: {e}", exc_info=True)
        sys.stdout.flush()
        raise


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    import sys
    user = update.effective_user
    logger.info(f"Showing main menu for user {user.id}")
    sys.stdout.flush()
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить объект", callback_data="add_object")],
        [InlineKeyboardButton("📋 Мои объекты", callback_data="my_objects")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("🔑 Получить код для веба", callback_data="getcode")],
    ]
    
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Добро пожаловать! Выберите действие:"
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            logger.info(f"Edited message for user {user.id}")
        elif update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
            logger.info(f"Sent message to user {user.id}")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"Error showing main menu for user {user.id}: {e}", exc_info=True)
        sys.stdout.flush()
        raise


# Object creation moved to bot/handlers_object.py


async def getcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить код для привязки к веб-интерфейсу"""
    user_id = str(update.effective_user.id)
    
    try:
        code = generate_web_code(user_id)
        # Use monospace font for code (HTML <code> tag)
        text = f"Ваш код для входа в веб-интерфейс:\n\n<code>{code}</code>\n\nКод действителен 10 минут.\n\nНажмите на код, чтобы скопировать."
        
        # Log action
        try:
            db = get_db()
            try:
                user = get_user(user_id)
                if user:
                    action_log = ActionLog(
                        user_id=user.user_id,
                        action='bot_getcode_requested',
                        details_json={'telegram_id': int(user_id), 'code': code},
                        created_at=datetime.utcnow()
                    )
                    db.add(action_log)
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to log getcode action: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to get DB session for logging: {e}")
        
        if update.message:
            await update.message.reply_text(text, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in getcode_command: {e}", exc_info=True)
        error_text = f"Ошибка при генерации кода: {str(e)}"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.answer(error_text, show_alert=True)

