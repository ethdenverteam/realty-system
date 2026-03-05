"""
Обработчики команд Telegram бота
Цель: обработка команд пользователя и логирование всех действий для анализа
"""
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_user, update_user_activity, generate_web_code
from bot.config import ADMIN_ID
from bot.utils_logger import log_bot_action, log_bot_error

logger = logging.getLogger('bot.handlers')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start - точка входа пользователя в бота
    Логика: обновляет активность пользователя, проверяет параметры, показывает меню или генерирует код
    """
    user = update.effective_user
    telegram_id = str(user.id)
    
    # Логируем начало обработки команды В ТЕСТОВЫЙ ЛОГ
    logger.info(f"[START_COMMAND] Received /start command from user {user.id} (@{user.username})")
    logger.info(f"[START_COMMAND] Processing /start command - user_id={user.id}, username=@{user.username}")
    logger.debug(f"[START_COMMAND] Update type: {type(update)}, Message: {update.message}, CallbackQuery: {update.callback_query}")
    logger.debug(f"[START_COMMAND] Context args: {context.args}")
    sys.stdout.flush()
    
    try:
        log_bot_action(
            action='bot_command_start',
            telegram_id=telegram_id,
            username=user.username,
            details={'args': context.args or []}
        )
    except Exception as e:
        logger.warning(f"[START_COMMAND] Failed to log action: {e}", exc_info=True)
    
    sys.stdout.flush()
    
    try:
        logger.debug(f"[START_COMMAND] Step 1: Updating user activity for {telegram_id}")
        # Обновляем активность пользователя в БД
        update_user_activity(telegram_id, user.username)
        logger.debug(f"[START_COMMAND] Step 2: User activity updated")
        
        # Проверяем параметр start: если 'getcode', сразу генерируем код
        if context.args and len(context.args) > 0 and context.args[0] == 'getcode':
            logger.info(f"[START_COMMAND] Start parameter 'getcode' detected for user {user.id}")
            await getcode_command(update, context)
        else:
            # Иначе показываем главное меню
            logger.debug(f"[START_COMMAND] Step 3: Showing main menu for user {user.id}")
            await show_main_menu(update, context)
        
        logger.info(f"[START_COMMAND] Successfully processed /start for user {user.id}")
        logger.info(f"[START_COMMAND] Response sent to user {user.id}")
        sys.stdout.flush()
    except Exception as e:
        # Логируем ошибку с полным контекстом В ТЕСТОВЫЙ ЛОГ
        logger.error(f"[START_COMMAND] Error in start_command for user {user.id}: {e}", exc_info=True)
        logger.error(f"[START_COMMAND] Failed to process /start command - user_id={user.id}, error={str(e)}")
        log_bot_error(
            error=e,
            action='bot_command_start',
            telegram_id=telegram_id,
            username=user.username
        )
        sys.stdout.flush()
        raise


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать главное меню бота
    Логика: формирует клавиатуру с основными действиями, добавляет админ-панель для админа
    """
    user = update.effective_user
    telegram_id = str(user.id)
    
    logger.info(f"Showing main menu for user {user.id}")
    log_bot_action(
        action='bot_menu_main_shown',
        telegram_id=telegram_id,
        username=user.username
    )
    sys.stdout.flush()
    
    # Формируем клавиатуру с основными действиями
    keyboard = [
        [InlineKeyboardButton("➕ Добавить объект", callback_data="add_object")],
        [InlineKeyboardButton("📋 Мои объекты", callback_data="my_objects")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("🔑 Получить код для веба", callback_data="getcode")],
    ]
    
    # Добавляем админ-панель только для администратора
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Добро пожаловать! Выберите действие:"
    
    try:
        logger.debug(f"[SHOW_MAIN_MENU] Step 1: Preparing to send message")
        # Отправляем или редактируем сообщение в зависимости от типа update
        if update.callback_query:
            logger.debug(f"[SHOW_MAIN_MENU] Step 2: Editing callback query message")
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            logger.info(f"[SHOW_MAIN_MENU] Edited message for user {user.id}")
        elif update.message:
            logger.debug(f"[SHOW_MAIN_MENU] Step 2: Replying to message")
            await update.message.reply_text(text, reply_markup=reply_markup)
            logger.info(f"[SHOW_MAIN_MENU] Sent message to user {user.id}")
        else:
            logger.warning(f"[SHOW_MAIN_MENU] No message or callback_query in update")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"[SHOW_MAIN_MENU] Error showing main menu for user {user.id}: {e}", exc_info=True)
        try:
            log_bot_error(
                error=e,
                action='bot_menu_main_shown',
                telegram_id=telegram_id,
                username=user.username
            )
        except Exception as log_err:
            logger.error(f"[SHOW_MAIN_MENU] Failed to log error: {log_err}")
        sys.stdout.flush()
        raise


# Object creation moved to bot/handlers_object.py


async def getcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Генерация кода для привязки бота к веб-интерфейсу
    Логика: генерирует временный код (действителен 10 минут), сохраняет в БД, отправляет пользователю
    """
    user = update.effective_user
    telegram_id = str(user.id)
    
    logger.info(f"getcode command from user {user.id}")
    
    try:
        # Генерируем код для веб-интерфейса
        code = generate_web_code(telegram_id)
        
        # Формируем сообщение с кодом (моноширинный шрифт для удобства копирования)
        text = f"Ваш код для входа в веб-интерфейс:\n\n<code>{code}</code>\n\nКод действителен 10 минут.\n\nНажмите на код, чтобы скопировать."
        
        # Логируем действие в БД и файл
        user_obj = get_user(telegram_id)
        log_bot_action(
            action='bot_getcode_requested',
            user_id=user_obj.user_id if user_obj else None,
            telegram_id=telegram_id,
            username=user.username,
            details={'code': code, 'code_length': len(code)}
        )
        
        # Отправляем код пользователю
        if update.message:
            await update.message.reply_text(text, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, parse_mode='HTML')
        
        logger.info(f"Code generated successfully for user {user.id}")
        
    except Exception as e:
        # Логируем ошибку с полным контекстом
        logger.error(f"Error in getcode_command for user {user.id}: {e}", exc_info=True)
        log_bot_error(
            error=e,
            action='bot_getcode_requested',
            telegram_id=telegram_id,
            username=user.username
        )
        
        # Отправляем сообщение об ошибке пользователю
        error_text = f"Ошибка при генерации кода: {str(e)}"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.answer(error_text, show_alert=True)

