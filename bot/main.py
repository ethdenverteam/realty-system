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
    start_command, show_main_menu, add_object_start,
    getcode_command
)
from bot.config import BOT_TOKEN, ADMIN_ID

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("getcode", getcode_command))
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(add_object_start, pattern="^add_object$"))
    
    # Add more handlers from botOLD.py as needed
    # TODO: Port all handlers from botOLD.py
    
    # Start bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

