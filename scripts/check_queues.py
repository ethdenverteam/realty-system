"""
Скрипт для проверки состояния очередей автопубликации
Использование: python scripts/check_queues.py [object_id]
"""
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from app.database import db
from app.models.autopublish_config import AutopublishConfig
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.publication_queue import PublicationQueue
from app.models.object import Object
from app.models.telegram_account import TelegramAccount
from app.models.chat import Chat
from datetime import datetime
from app.utils.time_utils import utc_to_msk


def check_autopublish_config(object_id=None):
    """Проверить конфигурацию автопубликации"""
    print("\n" + "="*80)
    print("ПРОВЕРКА КОНФИГУРАЦИИ АВТОПУБЛИКАЦИИ")
    print("="*80)
    
    with app.app_context():
        if object_id:
            configs = AutopublishConfig.query.filter_by(object_id=object_id).all()
        else:
            configs = AutopublishConfig.query.filter_by(enabled=True).limit(10).all()
        
        if not configs:
            print(f"❌ Не найдено конфигураций автопубликации для объекта {object_id or '(всех объектов)'}")
            return
        
        for cfg in configs:
            print(f"\n📋 Конфигурация ID: {cfg.config_id}")
            print(f"   Объект: {cfg.object_id}")
            print(f"   Пользователь: {cfg.user_id}")
            print(f"   Включена: {cfg.enabled}")
            print(f"   Бот включен: {cfg.bot_enabled}")
            
            # Проверяем объект
            obj = Object.query.get(cfg.object_id)
            if obj:
                print(f"   Статус объекта: {obj.status}")
            else:
                print(f"   ⚠️  Объект не найден в БД!")
            
            # Проверяем конфигурацию аккаунтов
            accounts_cfg = cfg.accounts_config_json or {}
            if isinstance(accounts_cfg, dict) and accounts_cfg.get('accounts'):
                print(f"   Аккаунты в конфиге: {len(accounts_cfg['accounts'])}")
                for acc_entry in accounts_cfg['accounts']:
                    account_id = acc_entry.get('account_id')
                    chat_ids = acc_entry.get('chat_ids', [])
                    account = TelegramAccount.query.get(account_id)
                    if account:
                        print(f"      - Аккаунт {account_id} ({account.phone}): {len(chat_ids)} чатов, режим: {account.mode}, активен: {account.is_active}")
                    else:
                        print(f"      - ⚠️  Аккаунт {account_id} не найден!")
            else:
                print(f"   ⚠️  Нет конфигурации аккаунтов")


def check_bot_queue(object_id=None):
    """Проверить очередь бота"""
    print("\n" + "="*80)
    print("ПРОВЕРКА ОЧЕРЕДИ БОТА (publication_queues)")
    print("="*80)
    
    with app.app_context():
        query = PublicationQueue.query.filter(
            PublicationQueue.type == 'bot',
            PublicationQueue.mode == 'autopublish'
        )
        
        if object_id:
            query = query.filter_by(object_id=object_id)
        
        queues = query.order_by(PublicationQueue.scheduled_time.asc()).limit(20).all()
        
        if not queues:
            print(f"❌ Нет задач в очереди бота для объекта {object_id or '(всех объектов)'}")
            return
        
        print(f"Найдено задач: {len(queues)}")
        for q in queues:
            scheduled_msk = utc_to_msk(q.scheduled_time) if q.scheduled_time else None
            scheduled_str = scheduled_msk.strftime('%Y-%m-%d %H:%M:%S МСК') if scheduled_msk else 'не запланировано'
            
            print(f"\n📌 Задача {q.queue_id}")
            print(f"   Объект: {q.object_id}")
            print(f"   Чат: {q.chat_id}")
            print(f"   Статус: {q.status}")
            print(f"   Запланировано: {scheduled_str}")
            print(f"   Попытки: {q.attempts}")
            if q.error_message:
                print(f"   ⚠️  Ошибка: {q.error_message[:100]}")


def check_account_queues(object_id=None, account_phone=None):
    """Проверить очереди аккаунтов"""
    print("\n" + "="*80)
    print("ПРОВЕРКА ОЧЕРЕДЕЙ АККАУНТОВ (account_publication_queues)")
    print("="*80)
    
    with app.app_context():
        query = AccountPublicationQueue.query
        
        if object_id:
            query = query.filter_by(object_id=object_id)
        
        if account_phone:
            account = TelegramAccount.query.filter_by(phone=account_phone).first()
            if account:
                query = query.filter_by(account_id=account.account_id)
            else:
                print(f"❌ Аккаунт с телефоном {account_phone} не найден")
                return
        
        queues = query.order_by(
            AccountPublicationQueue.account_id.asc(),
            AccountPublicationQueue.scheduled_time.asc()
        ).limit(50).all()
        
        if not queues:
            print(f"❌ Нет задач в очередях аккаунтов для объекта {object_id or '(всех объектов)'}")
            return
        
        # Группируем по аккаунтам
        by_account = {}
        for q in queues:
            if q.account_id not in by_account:
                by_account[q.account_id] = []
            by_account[q.account_id].append(q)
        
        print(f"Найдено задач: {len(queues)} в {len(by_account)} аккаунтах")
        
        for account_id, account_queues in by_account.items():
            account = TelegramAccount.query.get(account_id)
            if account:
                print(f"\n📱 Аккаунт {account_id} ({account.phone})")
                print(f"   Режим: {account.mode}, Лимит: {account.daily_limit}, Активен: {account.is_active}")
                if account.last_error:
                    print(f"   ⚠️  Последняя ошибка: {account.last_error[:100]}")
            else:
                print(f"\n📱 Аккаунт {account_id} (не найден в БД)")
            
            # Статистика по статусам
            statuses = {}
            for q in account_queues:
                statuses[q.status] = statuses.get(q.status, 0) + 1
            
            print(f"   Статусы: {statuses}")
            
            # Показываем первые 5 задач
            for q in account_queues[:5]:
                scheduled_msk = utc_to_msk(q.scheduled_time) if q.scheduled_time else None
                scheduled_str = scheduled_msk.strftime('%Y-%m-%d %H:%M:%S МСК') if scheduled_msk else 'не запланировано'
                
                print(f"      - Задача {q.queue_id}: объект {q.object_id}, чат {q.chat_id}, статус {q.status}, время {scheduled_str}")
                if q.error_message:
                    print(f"        ⚠️  Ошибка: {q.error_message[:80]}")
            
            if len(account_queues) > 5:
                print(f"      ... и еще {len(account_queues) - 5} задач")


def main():
    """Главная функция"""
    object_id = sys.argv[1] if len(sys.argv) > 1 else None
    account_phone = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("\n" + "="*80)
    print("ДИАГНОСТИКА ОЧЕРЕДЕЙ АВТОПУБЛИКАЦИИ")
    print("="*80)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if object_id:
        print(f"Объект: {object_id}")
    if account_phone:
        print(f"Аккаунт: {account_phone}")
    
    try:
        check_autopublish_config(object_id)
        check_bot_queue(object_id)
        check_account_queues(object_id, account_phone)
        
        print("\n" + "="*80)
        print("ПРОВЕРКА ЗАВЕРШЕНА")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

