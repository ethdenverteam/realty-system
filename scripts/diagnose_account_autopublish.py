#!/usr/bin/env python3
"""
Скрипт диагностики автопубликации от имени аккаунтов
Проверяет состояние account_publication_queues и связанных данных
"""
import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, database as app_db
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.telegram_account import TelegramAccount
from app.models.autopublish_config import AutopublishConfig
from app.models.object import Object
from app.models.chat import Chat
from app.models.publication_history import PublicationHistory
from sqlalchemy import func

def diagnose_account_autopublish():
    """Диагностика состояния автопубликации от имени аккаунтов"""
    
    with app.app_context():
        print("=" * 80)
        print("ДИАГНОСТИКА АВТОПУБЛИКАЦИИ ОТ ИМЕНИ АККАУНТОВ")
        print("=" * 80)
        print()
        
        now = datetime.utcnow()
        print(f"Текущее время UTC: {now}")
        print()
        
        # 1. Проверка активных аккаунтов
        print("1. АКТИВНЫЕ АККАУНТЫ")
        print("-" * 80)
        active_accounts = app_db.session.query(TelegramAccount).filter_by(is_active=True).all()
        print(f"Всего активных аккаунтов: {len(active_accounts)}")
        
        for acc in active_accounts:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_pubs = app_db.session.query(
                func.count(PublicationHistory.history_id)
            ).filter(
                PublicationHistory.account_id == acc.account_id,
                PublicationHistory.published_at >= today_start,
                PublicationHistory.deleted == False
            ).scalar() or 0
            
            print(f"  - Account {acc.account_id} ({acc.phone}):")
            print(f"    Режим: {acc.mode}")
            print(f"    Дневной лимит: {acc.daily_limit}")
            print(f"    Публикаций сегодня: {today_pubs}/{acc.daily_limit}")
            print(f"    Последнее использование: {acc.last_used}")
            print(f"    Последняя ошибка: {acc.last_error}")
        print()
        
        # 2. Проверка очередей публикаций
        print("2. ОЧЕРЕДИ ПУБЛИКАЦИЙ (account_publication_queues)")
        print("-" * 80)
        
        total_queues = app_db.session.query(AccountPublicationQueue).count()
        pending_queues = app_db.session.query(AccountPublicationQueue).filter_by(status='pending').count()
        processing_queues = app_db.session.query(AccountPublicationQueue).filter_by(status='processing').count()
        completed_queues = app_db.session.query(AccountPublicationQueue).filter_by(status='completed').count()
        failed_queues = app_db.session.query(AccountPublicationQueue).filter_by(status='failed').count()
        
        print(f"Всего задач в очереди: {total_queues}")
        print(f"  - pending: {pending_queues}")
        print(f"  - processing: {processing_queues}")
        print(f"  - completed: {completed_queues}")
        print(f"  - failed: {failed_queues}")
        print()
        
        # 3. Готовые к публикации задачи
        print("3. ЗАДАЧИ, ГОТОВЫЕ К ПУБЛИКАЦИИ (scheduled_time <= now)")
        print("-" * 80)
        ready_queues = app_db.session.query(AccountPublicationQueue).filter(
            AccountPublicationQueue.status == 'pending',
            AccountPublicationQueue.scheduled_time <= now
        ).order_by(AccountPublicationQueue.scheduled_time.asc()).limit(20).all()
        
        print(f"Готовых к публикации: {len(ready_queues)}")
        if ready_queues:
            print("\nПервые 20 задач:")
            for q in ready_queues:
                account = app_db.session.query(TelegramAccount).get(q.account_id)
                obj = app_db.session.query(Object).get(q.object_id)
                chat = app_db.session.query(Chat).get(q.chat_id)
                
                print(f"  - Queue {q.queue_id}:")
                print(f"    Объект: {q.object_id} ({obj.address if obj else 'NOT FOUND'})")
                print(f"    Аккаунт: {q.account_id} ({account.phone if account else 'NOT FOUND'})")
                print(f"    Чат: {q.chat_id} ({chat.title if chat else 'NOT FOUND'})")
                print(f"    Запланировано: {q.scheduled_time}")
                print(f"    Попыток: {q.attempts}")
                print(f"    Создано: {q.created_at}")
        print()
        
        # 4. Застрявшие задачи (processing более 5 минут)
        print("4. ЗАСТРЯВШИЕ ЗАДАЧИ (processing более 5 минут)")
        print("-" * 80)
        stuck_threshold = now - timedelta(minutes=5)
        stuck_queues = app_db.session.query(AccountPublicationQueue).filter(
            AccountPublicationQueue.status == 'processing',
            AccountPublicationQueue.started_at < stuck_threshold
        ).all()
        
        print(f"Застрявших задач: {len(stuck_queues)}")
        if stuck_queues:
            print("\nЗастрявшие задачи:")
            for q in stuck_queues:
                account = app_db.session.query(TelegramAccount).get(q.account_id)
                print(f"  - Queue {q.queue_id}:")
                print(f"    Аккаунт: {q.account_id} ({account.phone if account else 'NOT FOUND'})")
                print(f"    Начато: {q.started_at}")
                print(f"    Прошло времени: {now - q.started_at}")
                print(f"    Попыток: {q.attempts}")
        print()
        
        # 5. Конфигурации автопубликации
        print("5. КОНФИГУРАЦИИ АВТОПУБЛИКАЦИИ")
        print("-" * 80)
        enabled_configs = app_db.session.query(AutopublishConfig).filter_by(enabled=True).count()
        total_configs = app_db.session.query(AutopublishConfig).count()
        
        print(f"Всего конфигураций: {total_configs}")
        print(f"Включено: {enabled_configs}")
        
        # Проверяем конфигурации с accounts_enabled
        configs_with_accounts = app_db.session.query(AutopublishConfig).filter(
            AutopublishConfig.enabled == True,
            AutopublishConfig.accounts_config_json.isnot(None)
        ).all()
        
        print(f"\nКонфигураций с включенными аккаунтами: {len(configs_with_accounts)}")
        for cfg in configs_with_accounts[:5]:  # Показываем первые 5
            accounts_cfg = cfg.accounts_config_json
            if isinstance(accounts_cfg, dict):
                accounts_list = accounts_cfg.get('accounts', [])
                print(f"  - Object {cfg.object_id}: {len(accounts_list)} аккаунтов")
        print()
        
        # 6. История публикаций за сегодня
        print("6. ИСТОРИЯ ПУБЛИКАЦИЙ ЗА СЕГОДНЯ")
        print("-" * 80)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_history = app_db.session.query(PublicationHistory).filter(
            PublicationHistory.account_id.isnot(None),
            PublicationHistory.published_at >= today_start,
            PublicationHistory.deleted == False
        ).all()
        
        print(f"Публикаций от имени аккаунтов сегодня: {len(today_history)}")
        
        # Группируем по аккаунтам
        by_account = {}
        for h in today_history:
            if h.account_id not in by_account:
                by_account[h.account_id] = []
            by_account[h.account_id].append(h)
        
        print(f"\nПо аккаунтам:")
        for account_id, pubs in by_account.items():
            account = app_db.session.query(TelegramAccount).get(account_id)
            print(f"  - Account {account_id} ({account.phone if account else 'NOT FOUND'}): {len(pubs)} публикаций")
        print()
        
        # 7. Рекомендации
        print("7. РЕКОМЕНДАЦИИ")
        print("-" * 80)
        
        if processing_queues > 0:
            print(f"⚠️  Обнаружено {processing_queues} задач в статусе 'processing'")
            if stuck_queues:
                print(f"   Из них {len(stuck_queues)} застряли (более 5 минут)")
                print("   Рекомендуется сбросить их в 'pending'")
        
        if pending_queues > 0 and len(active_accounts) == 0:
            print("⚠️  Есть задачи в очереди, но нет активных аккаунтов")
        
        if ready_queues and len(active_accounts) > 0:
            print(f"✅ Найдено {len(ready_queues)} задач, готовых к публикации")
            print("   Проверьте логи Celery для деталей обработки")
        
        if len(ready_queues) == 0 and pending_queues > 0:
            print(f"⚠️  Есть {pending_queues} задач в статусе 'pending', но ни одна не готова к публикации")
            print("   Проверьте scheduled_time задач")
        
        print()
        print("=" * 80)

if __name__ == '__main__':
    diagnose_account_autopublish()

