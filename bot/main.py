"""
Main bot file - адаптированная версия из botOLD.py
"""
import asyncio
import os
import sys
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram import Update

from bot.handlers_main import (
    start_command,
    show_main_menu,
    getcode_command,
)
from bot.handlers_object import create_object_conversation_handler
from bot.handlers_settings import create_settings_conversation_handler
from bot.handlers_objects_view import my_objects_command, my_objects_callback, edit_object_from_list
from bot.handlers.object_edit import (
    edit_price_handler, edit_area_handler, edit_floor_handler, edit_comment_handler,
    edit_residential_complex_handler, edit_renovation_handler, edit_address_handler, edit_contacts_handler,
    edit_rooms_handler, edit_district_handler, add_district_handler,
    add_media_handler, back_to_preview_handler,
    edit_price_input, edit_area_input, edit_floor_input, edit_comment_input,
    residential_complex_input, edit_rooms_selected, edit_district_selected,
    add_district_selected, renovation_selected, address_input,
    contacts_input, phone_from_settings_handler,
    phone_custom_handler, set_contact_name_handler, toggle_username_handler,
    delete_object_handler, confirm_delete_object_handler,
    OBJECT_WAITING_EDIT_ROOMS, OBJECT_WAITING_EDIT_DISTRICT, OBJECT_WAITING_EDIT_PRICE,
    OBJECT_WAITING_ADD_DISTRICT, OBJECT_WAITING_EDIT_AREA, OBJECT_WAITING_EDIT_FLOOR,
    OBJECT_WAITING_EDIT_COMMENT, OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX, OBJECT_PREVIEW_MENU
)
from bot.handlers_publication import (
    publish_immediate_handler, confirm_publish_handler
)
from bot.handlers_object import (
    object_area_input, object_floor_input, object_comment_input,
    object_media_received, skip_media,
    OBJECT_WAITING_AREA, OBJECT_WAITING_FLOOR, OBJECT_WAITING_COMMENT,
    OBJECT_WAITING_MEDIA, OBJECT_WAITING_RENOVATION, OBJECT_WAITING_ADDRESS,
    OBJECT_WAITING_CONTACTS
)
from bot.config import BOT_TOKEN, ADMIN_ID

# Импортируем единую систему логирования для бота
from bot.utils_logger import setup_bot_logging, log_bot_action, log_bot_error

# ВАЖНО: импортируем Flask-приложение, чтобы создать application context для работы с db.session
from app import app as flask_app

# Настраиваем логирование при старте модуля
logger = setup_bot_logging()


def main():
    """Main function to run the bot"""
    # Глобальный Flask application context для бота:
    # после унификации БД бот использует app.database.db.session и модели app.models,
    # поэтому все операции с БД должны выполняться внутри app_context().
    flask_app.app_context().push()

    # Create application
    # ВАЖНО: использовать drop_pending_updates=True и уникальный токен,
    # но контроль количества инстансов бота должен быть на уровне оркестрации (Docker/systemd).
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add error handler first
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors (с мягкой обработкой сетевых и конфликтных ошибок)"""
        error = context.error
        if not error:
            return

        error_name = error.__class__.__name__
        error_msg = str(error)
        
        # Логируем информацию об update
        update_info = "unknown"
        if isinstance(update, Update):
            if update.message:
                update_info = f"message from {update.effective_user.id if update.effective_user else 'unknown'}: {update.message.text or 'media'}"
            elif update.callback_query:
                update_info = f"callback_query from {update.effective_user.id if update.effective_user else 'unknown'}: {update.callback_query.data}"
            else:
                update_info = f"update type: {type(update)}"
        
        logger.debug(f"[ERROR_HANDLER] Processing error: {error_name} for {update_info}")

        # Конфликт getUpdates — признак второго инстанса, логируем мягко без трейсбека
        if 'Conflict' in error_name or 'Conflict' in error_msg or 'getUpdates' in error_msg:
            logger.warning(f"[ERROR_HANDLER] Bot getUpdates conflict detected (probably multiple instances): {error_msg}")
            return

        # Сетевые ошибки Telegram (Bad Gateway, ConnectError) — логируем как warning
        network_keywords = ['Bad Gateway', 'ConnectError', 'NetworkError', 'All connection attempts failed']
        if any(k in error_msg for k in network_keywords):
            logger.warning(f"[ERROR_HANDLER] Transient network error while handling update: {error_msg}")
            return

        # Остальное — полноценный error с трейсбеком
        logger.error(f"[ERROR_HANDLER] Exception while handling an update ({update_info}): {error}", exc_info=error)
        
        # Логируем в test_bot_errors.log через test handler
        try:
            error_logger = logging.getLogger('bot.errors')
            error_logger.error(f"Error in update {update_info}: {error_name}: {error_msg}", exc_info=error)
        except Exception as e:
            logger.error(f"Failed to log error to test_bot_errors.log: {e}")
    
    application.add_error_handler(error_handler)
    
    # Register handlers
    logger.info("Registering command handlers...")
    
    # ВАЖНО: Сначала регистрируем обработчики команд, потом логирование
    # Обработчики команд должны быть в группе по умолчанию (0) или выше
    logger.info("Registering /start command handler...")
    application.add_handler(CommandHandler("start", start_command))
    logger.info("Registering /getcode command handler...")
    application.add_handler(CommandHandler("getcode", getcode_command))
    
    # Добавляем логирование всех входящих команд ПОСЛЕ регистрации обработчиков
    # Используем низкий приоритет, чтобы не блокировать обработку
    async def log_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Логируем все входящие команды (не блокируем обработку)"""
        if update.message and update.message.text:
            command = update.message.text.split()[0] if update.message.text.split() else ""
            user = update.effective_user
            logger.info(f"[LOG_COMMAND] COMMAND_RECEIVED: {command} from user {user.id if user else 'unknown'} (@{user.username if user else 'unknown'})")
            logger.info(f"[LOG_COMMAND] User sent command: {command} - user_id={user.id if user else 'unknown'}, text={update.message.text}")
            sys.stdout.flush()
        # НЕ блокируем обработку - просто логируем
    
    # Добавляем обработчик логирования команд с низким приоритетом (после обработчиков команд)
    application.add_handler(MessageHandler(filters.COMMAND, log_command_handler), group=-1)
    logger.info("Registering /myobjects command handler...")
    application.add_handler(CommandHandler("myobjects", my_objects_command))
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(getcode_command, pattern="^getcode$"))
    application.add_handler(CallbackQueryHandler(my_objects_callback, pattern="^(my_objects|my_objects_page_|edit_object_from_list_)"))
    # Register publish and delete handlers outside conversation for list view
    from bot.handlers_publication import publish_immediate_handler
    from bot.handlers.object_edit import delete_object_handler, confirm_delete_object_handler
    application.add_handler(CallbackQueryHandler(publish_immediate_handler, pattern="^publish_immediate_"))
    application.add_handler(CallbackQueryHandler(delete_object_handler, pattern="^delete_object_"))
    application.add_handler(CallbackQueryHandler(confirm_delete_object_handler, pattern="^confirm_delete_"))
    
    # Add object creation conversation handler
    logger.info("Registering conversation handlers...")
    application.add_handler(create_object_conversation_handler())
    application.add_handler(create_settings_conversation_handler())
    
    # Add object editing handlers
    logger.info("Registering object editing handlers...")
    from telegram.ext import ConversationHandler as ConvHandler
    
    # Edit conversation handler for editing states
    # NOTE: All edit handlers must be inside ConversationHandler to properly handle states
    edit_conversation = ConvHandler(
        entry_points=[
            CallbackQueryHandler(edit_object_from_list, pattern="^edit_object_from_list_"),
            CallbackQueryHandler(edit_price_handler, pattern="^edit_price_"),
            CallbackQueryHandler(edit_area_handler, pattern="^edit_area_"),
            CallbackQueryHandler(edit_floor_handler, pattern="^edit_floor_"),
            CallbackQueryHandler(edit_comment_handler, pattern="^edit_comment_"),
            CallbackQueryHandler(edit_residential_complex_handler, pattern="^edit_residential_complex_"),
            CallbackQueryHandler(edit_renovation_handler, pattern="^edit_renovation_"),
            CallbackQueryHandler(edit_address_handler, pattern="^edit_address_"),
            CallbackQueryHandler(edit_contacts_handler, pattern="^edit_contacts_"),
            CallbackQueryHandler(edit_rooms_handler, pattern="^edit_rooms_"),
            CallbackQueryHandler(edit_district_handler, pattern="^edit_district_"),
            CallbackQueryHandler(add_district_handler, pattern="^add_district_"),
            CallbackQueryHandler(add_media_handler, pattern="^add_media_"),
        ],
        states={
            OBJECT_WAITING_EDIT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_price_input)
            ],
            OBJECT_WAITING_EDIT_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_area_input)
            ],
            OBJECT_WAITING_EDIT_FLOOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_floor_input)
            ],
            OBJECT_WAITING_EDIT_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_comment_input)
            ],
            OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, residential_complex_input)
            ],
            OBJECT_WAITING_RENOVATION: [
                CallbackQueryHandler(renovation_selected, pattern="^renovation_")
            ],
            OBJECT_WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, address_input)
            ],
            OBJECT_WAITING_CONTACTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, contacts_input),
                CallbackQueryHandler(phone_from_settings_handler, pattern="^phone_from_settings_"),
                CallbackQueryHandler(phone_custom_handler, pattern="^phone_custom_"),
                CallbackQueryHandler(set_contact_name_handler, pattern="^set_contact_name_"),
                CallbackQueryHandler(toggle_username_handler, pattern="^toggle_username_"),
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$"),
            ],
            OBJECT_WAITING_EDIT_ROOMS: [
                CallbackQueryHandler(edit_rooms_selected, pattern="^rooms_")
            ],
            OBJECT_WAITING_EDIT_DISTRICT: [
                CallbackQueryHandler(edit_district_selected, pattern="^district_")
            ],
            OBJECT_WAITING_ADD_DISTRICT: [
                CallbackQueryHandler(add_district_selected, pattern="^district_")
            ],
            OBJECT_WAITING_MEDIA: [
                MessageHandler(filters.PHOTO, object_media_received),
                CallbackQueryHandler(skip_media, pattern="^skip_media$")
            ],
            OBJECT_PREVIEW_MENU: [
                CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$"),
                CallbackQueryHandler(edit_price_handler, pattern="^edit_price_"),
                CallbackQueryHandler(edit_area_handler, pattern="^edit_area_"),
                CallbackQueryHandler(edit_floor_handler, pattern="^edit_floor_"),
                CallbackQueryHandler(edit_comment_handler, pattern="^edit_comment_"),
                CallbackQueryHandler(edit_residential_complex_handler, pattern="^edit_residential_complex_"),
                CallbackQueryHandler(edit_renovation_handler, pattern="^edit_renovation_"),
                CallbackQueryHandler(edit_address_handler, pattern="^edit_address_"),
                CallbackQueryHandler(edit_contacts_handler, pattern="^edit_contacts_"),
                CallbackQueryHandler(edit_rooms_handler, pattern="^edit_rooms_"),
                CallbackQueryHandler(edit_district_handler, pattern="^edit_district_"),
                CallbackQueryHandler(add_district_handler, pattern="^add_district_"),
                CallbackQueryHandler(add_media_handler, pattern="^add_media_"),
                CallbackQueryHandler(phone_from_settings_handler, pattern="^phone_from_settings_"),
                CallbackQueryHandler(phone_custom_handler, pattern="^phone_custom_"),
                CallbackQueryHandler(set_contact_name_handler, pattern="^set_contact_name_"),
                CallbackQueryHandler(toggle_username_handler, pattern="^toggle_username_"),
                CallbackQueryHandler(publish_immediate_handler, pattern="^publish_immediate_"),
                CallbackQueryHandler(confirm_publish_handler, pattern="^confirm_publish_"),
                CallbackQueryHandler(delete_object_handler, pattern="^delete_object_"),
                CallbackQueryHandler(confirm_delete_object_handler, pattern="^confirm_delete_"),
            ],
            OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, residential_complex_input)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$"),
            MessageHandler(filters.COMMAND, back_to_preview_handler)
        ],
        name="edit_object_handler"
    )
    application.add_handler(edit_conversation)
    
    # Save chats from updates to database
    # ВАЖНО: Делаем это асинхронно и не блокируем обработку сообщений
    async def save_chat_from_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save chat from update to database (async, non-blocking)"""
        from bot.utils_chat import save_chat_from_update as save_chat
        try:
            # Выполняем синхронную операцию в executor, чтобы не блокировать event loop
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, save_chat, update)
        except Exception as e:
            logger.error(f"Error saving chat from update: {e}", exc_info=True)
    
    # Add chat saver handler - должен выполняться для всех обновлений, но не блокировать
    # Используем низкий приоритет, чтобы не мешать обработке команд
    application.add_handler(MessageHandler(filters.ALL, save_chat_from_update), group=-1)
    application.add_handler(CallbackQueryHandler(save_chat_from_update), group=-1)
    
    # Log all updates (for debugging) - only non-command messages to avoid duplication
    # NOTE: This handler should be added AFTER conversation handlers to avoid intercepting messages
    async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log all incoming updates (non-commands only)"""
        import sys
        # Skip commands - they're already logged in handlers
        # Skip if in conversation - check if any conversation handler is active
        # Conversation handlers store state in context.user_data with conversation name
        if context.user_data:
            # Check if any conversation is active
            for key in context.user_data.keys():
                if key.startswith('_conversation_'):
                    return  # Don't log if in conversation
        
        if update.message:
            if not update.message.text or not update.message.text.startswith('/'):
                logger.debug(f"Received message from {update.effective_user.id}: {update.message.text or 'media'}")
        elif update.callback_query:
            # Callback queries are already logged, skip
            pass
        sys.stdout.flush()
    
    # Add update logger LAST with lowest priority, only for non-command text messages
    # This ensures conversation handlers process messages first
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_update), group=-1)
    
    logger.info("All handlers registered successfully")
    
    # Add more handlers from botOLD.py as needed
    # TODO: Port all handlers from botOLD.py
    
    # Start bot
    logger.info("Bot started successfully, starting polling...")
    import sys
    sys.stdout.flush()
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()

