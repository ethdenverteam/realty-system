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
from bot.handlers_objects_view import my_objects_command, my_objects_callback
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
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
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
    application.add_handler(CallbackQueryHandler(my_objects_callback, pattern="^my_objects$"))
    
    # Add object creation conversation handler
    logger.info("Registering conversation handlers...")
    application.add_handler(create_object_conversation_handler())
    
    # Log all updates (for debugging)
    async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log all incoming updates"""
        import sys
        if update.message:
            logger.info(f"Received message from {update.effective_user.id}: {update.message.text or 'media'}")
        elif update.callback_query:
            logger.info(f"Received callback_query from {update.effective_user.id}: {update.callback_query.data}")
        sys.stdout.flush()
    
    # Add update logger (lowest priority)
    application.add_handler(MessageHandler(filters.ALL, log_update), group=-1)
    application.add_handler(CallbackQueryHandler(log_update, pattern=".*"), group=-1)
    
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

