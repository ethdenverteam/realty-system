"""
Bot configuration
"""
import os

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))

# Роли пользователей
ROLE_START = "start"
ROLE_BROKE = "broke"
ROLE_BEGINNER = "beginner"
ROLE_FREE = "free"
ROLE_FREEPREMIUM = "freepremium"
ROLE_PREMIUM = "premium"
ROLE_PROTIME = "protime"

# Лимиты Telegram
TELEGRAM_MESSAGES_PER_MINUTE = 20
TELEGRAM_MESSAGE_INTERVAL = 60 / TELEGRAM_MESSAGES_PER_MINUTE

