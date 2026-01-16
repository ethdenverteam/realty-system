"""
Main bot file - адаптированная версия из botOLD.py
"""
import asyncio
import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

from bot.handlers import (
    start_command, show_main_menu,
    getcode_command
)
from bot.handlers_object import create_object_conversation_handler
from bot.handlers_objects_view import my_objects_command, my_objects_callback, edit_object_from_list
from bot.handlers_object_edit import (
    edit_price_handler, edit_area_handler, edit_floor_handler, edit_comment_handler,
    edit_renovation_handler, edit_address_handler, edit_contacts_handler,
    edit_rooms_handler, edit_district_handler, add_district_handler,
    add_media_handler, back_to_preview_handler,
    edit_price_input, edit_rooms_selected, edit_district_selected,
    add_district_selected, renovation_selected, address_input,
    contacts_input, phone_from_settings_handler,
    phone_custom_handler, set_contact_name_handler, toggle_username_handler,
    OBJECT_WAITING_EDIT_ROOMS, OBJECT_WAITING_EDIT_DISTRICT, OBJECT_WAITING_EDIT_PRICE,
    OBJECT_WAITING_ADD_DISTRICT, OBJECT_PREVIEW_MENU
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

# Setup logging
import os
from logging.handlers import RotatingFileHandler

def setup_bot_logging():
    """Setup bot logging"""
    # Create logs directory
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Root logger
    logger = logging.getLogger('bot')
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-30s | %(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - use sys.stdout for docker-compose logs (unbuffered)
    import sys
    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # INFO level for console
    console_handler.setFormatter(simple_formatter)
    # Force immediate flush
    console_handler.stream = sys.stdout
    
    # File handler - all logs (with immediate flush)
    all_logs_file = os.path.join(log_dir, 'bot.log')
    file_handler = RotatingFileHandler(
        all_logs_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8',
        delay=False  # Don't delay opening file
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    # Force flush after each write
    file_handler.terminator = '\n'
    
    # Error handler
    error_logs_file = os.path.join(log_dir, 'bot_errors.log')
    error_handler = RotatingFileHandler(
        error_logs_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # ========== TEST LOGS (cleared on deploy) ==========
    
    # Test bot logs - cleared on each deploy
    test_bot_logs_file = os.path.join(log_dir, 'test_bot.log')
    test_bot_handler = logging.FileHandler(
        test_bot_logs_file,
        mode='a',  # Append mode (will be cleared by deploy.sh)
        encoding='utf-8'
    )
    test_bot_handler.setLevel(logging.DEBUG)
    test_bot_handler.setFormatter(detailed_formatter)
    
    # Test bot errors log
    test_bot_errors_file = os.path.join(log_dir, 'test_bot_errors.log')
    test_bot_errors_handler = logging.FileHandler(
        test_bot_errors_file,
        mode='a',  # Append mode (will be cleared by deploy.sh)
        encoding='utf-8'
    )
    test_bot_errors_handler.setLevel(logging.ERROR)
    test_bot_errors_handler.setFormatter(detailed_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(test_bot_handler)
    logger.addHandler(test_bot_errors_handler)
    
    # Set levels for libraries
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    # Ensure bot.handlers logger uses bot logger (but don't add duplicate handlers)
    handlers_logger = logging.getLogger('bot.handlers')
    handlers_logger.setLevel(logging.DEBUG)
    # Don't add handlers - let it propagate to parent 'bot' logger
    handlers_logger.propagate = True
    
    return logger

logger = setup_bot_logging()


def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add error handler first
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    application.add_error_handler(error_handler)
    
    # Register handlers
    logger.info("Registering command handlers...")
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("getcode", getcode_command))
    application.add_handler(CommandHandler("myobjects", my_objects_command))
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(getcode_command, pattern="^getcode$"))
    application.add_handler(CallbackQueryHandler(my_objects_callback, pattern="^(my_objects|my_objects_page_|edit_object_from_list_)"))
    
    # Add object creation conversation handler
    logger.info("Registering conversation handlers...")
    application.add_handler(create_object_conversation_handler())
    
    # Add object editing handlers
    logger.info("Registering object editing handlers...")
    from telegram.ext import ConversationHandler as ConvHandler
    
    # Edit handlers - callback queries
    application.add_handler(CallbackQueryHandler(edit_price_handler, pattern="^edit_price_"))
    application.add_handler(CallbackQueryHandler(edit_area_handler, pattern="^edit_area_"))
    application.add_handler(CallbackQueryHandler(edit_floor_handler, pattern="^edit_floor_"))
    application.add_handler(CallbackQueryHandler(edit_comment_handler, pattern="^edit_comment_"))
    application.add_handler(CallbackQueryHandler(edit_renovation_handler, pattern="^edit_renovation_"))
    application.add_handler(CallbackQueryHandler(edit_address_handler, pattern="^edit_address_"))
    application.add_handler(CallbackQueryHandler(edit_contacts_handler, pattern="^edit_contacts_"))
    application.add_handler(CallbackQueryHandler(edit_rooms_handler, pattern="^edit_rooms_"))
    application.add_handler(CallbackQueryHandler(edit_district_handler, pattern="^edit_district_"))
    application.add_handler(CallbackQueryHandler(add_district_handler, pattern="^add_district_"))
    application.add_handler(CallbackQueryHandler(add_media_handler, pattern="^add_media_"))
    application.add_handler(CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$"))
    application.add_handler(CallbackQueryHandler(phone_from_settings_handler, pattern="^phone_from_settings_"))
    application.add_handler(CallbackQueryHandler(phone_custom_handler, pattern="^phone_custom_"))
    application.add_handler(CallbackQueryHandler(set_contact_name_handler, pattern="^set_contact_name_"))
    application.add_handler(CallbackQueryHandler(toggle_username_handler, pattern="^toggle_username_"))
    application.add_handler(CallbackQueryHandler(publish_immediate_handler, pattern="^publish_immediate_"))
    application.add_handler(CallbackQueryHandler(confirm_publish_handler, pattern="^confirm_publish_"))
    
    # Edit conversation handler for editing states
    edit_conversation = ConvHandler(
        entry_points=[
            CallbackQueryHandler(edit_price_handler, pattern="^edit_price_"),
            CallbackQueryHandler(edit_area_handler, pattern="^edit_area_"),
            CallbackQueryHandler(edit_floor_handler, pattern="^edit_floor_"),
            CallbackQueryHandler(edit_comment_handler, pattern="^edit_comment_"),
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
            OBJECT_WAITING_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, object_area_input)
            ],
            OBJECT_WAITING_FLOOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, object_floor_input)
            ],
            OBJECT_WAITING_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, object_comment_input)
            ],
            OBJECT_WAITING_RENOVATION: [
                CallbackQueryHandler(renovation_selected, pattern="^renovation_")
            ],
            OBJECT_WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, address_input)
            ],
            OBJECT_WAITING_CONTACTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, contacts_input),
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
            ]
        },
        fallbacks=[
            CallbackQueryHandler(back_to_preview_handler, pattern="^back_to_preview$"),
            MessageHandler(filters.COMMAND, back_to_preview_handler)
        ],
        name="edit_object_handler"
    )
    application.add_handler(edit_conversation)
    
    # Log all updates (for debugging) - only non-command messages to avoid duplication
    async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log all incoming updates (non-commands only)"""
        import sys
        # Skip commands - they're already logged in handlers
        if update.message:
            if not update.message.text or not update.message.text.startswith('/'):
                logger.debug(f"Received message from {update.effective_user.id}: {update.message.text or 'media'}")
        elif update.callback_query:
            # Callback queries are already logged, skip
            pass
        sys.stdout.flush()
    
    # Add update logger (lowest priority, only for non-command text messages)
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

