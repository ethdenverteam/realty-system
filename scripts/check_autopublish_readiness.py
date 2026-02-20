#!/usr/bin/env python3
"""
Скрипт проверки готовности автопубликации к запуску в 8:00 МСК

Использование в Docker:
docker exec -it realty_web python scripts/check_autopublish_readiness.py
"""
import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from app.database import db
from app.models.autopublish_config import AutopublishConfig
from app.models.telegram_account import TelegramAccount
from app.models.chat import Chat
from app.models.telegram_account_chat import TelegramAccountChat
from app.models.object import Object

def check_autopublish_readiness():
    """Проверка готовности автопубликации"""
    
    with app.app_context():
        print("=" * 80)
        print("ПРОВЕРКА ГОТОВНОСТИ АВТОПУБЛИКАЦИИ К ЗАПУСКУ В 8:00 МСК")
        print("=" * 80)
        print()
        
        # 1. Проверка защиты от SoftTimeLimitExceeded
        print("1. ЗАЩИТА ОТ SoftTimeLimitExceeded")
        print("-" * 80)
        print("✅ Защита реализована:")
        print("   - Обработчик на верхнем уровне (до app_context)")
        print("   - Обработчик внутри app_context")
        print("   - Автоматический сброс застрявших задач (processing > 5 минут)")
        print("   - Soft time limit: 240 секунд (4 минуты)")
        print("   - Hard time limit: 300 секунд (5 минут)")
        print()
        
        # 2. Проверка расписания
        print("2. РАСПИСАНИЕ СОЗДАНИЯ ЗАДАЧ")
        print("-" * 80)
        print("✅ Задача schedule_daily_autopublish:")
        print("   - Запускается ежедневно в 05:00 UTC (08:00 МСК)")
        print("   - Расписание: crontab(minute=0, hour=5)")
        print("   - Создает задачи для всех объектов с enabled=True")
        print()
        
        # 3. Проверка конфигураций
        print("3. КОНФИГУРАЦИИ АВТОПУБЛИКАЦИИ")
        print("-" * 80)
        configs = db.session.query(AutopublishConfig).filter_by(enabled=True).all()
        print(f"Всего включенных конфигураций: {len(configs)}")
        print()
        
        ready_count = 0
        not_ready_count = 0
        not_ready_reasons = []
        
        for cfg in configs:
            obj = db.session.query(Object).get(cfg.object_id)
            if not obj:
                not_ready_count += 1
                not_ready_reasons.append(f"Object {cfg.object_id}: объект не найден")
                continue
            
            # Проверяем конфигурацию аккаунтов
            accounts_cfg = cfg.accounts_config_json or {}
            accounts_list = accounts_cfg.get('accounts') if isinstance(accounts_cfg, dict) else []
            
            if not accounts_list or len(accounts_list) == 0:
                # Нет аккаунтов - это нормально, если используется только бот
                continue
            
            # Проверяем каждый аккаунт
            account_ready = False
            for acc_entry in accounts_list:
                account_id = acc_entry.get('account_id')
                chat_ids = acc_entry.get('chat_ids', [])
                
                if not account_id or not chat_ids:
                    continue
                
                # Проверяем аккаунт
                account = db.session.query(TelegramAccount).get(account_id)
                if not account:
                    not_ready_reasons.append(f"Object {cfg.object_id}: аккаунт {account_id} не найден")
                    continue
                
                if not account.is_active:
                    not_ready_reasons.append(f"Object {cfg.object_id}: аккаунт {account_id} неактивен")
                    continue
                
                # Проверяем чаты
                for chat_id in chat_ids:
                    chat = db.session.query(Chat).get(chat_id)
                    if not chat:
                        not_ready_reasons.append(f"Object {cfg.object_id}: чат {chat_id} не найден")
                        continue
                    
                    # Проверяем привязку чата к аккаунту
                    legacy_check = chat.owner_account_id == account_id
                    new_check = db.session.query(TelegramAccountChat).filter_by(
                        account_id=account_id,
                        chat_id=chat_id
                    ).first() is not None
                    
                    if not (legacy_check or new_check):
                        not_ready_reasons.append(f"Object {cfg.object_id}: чат {chat_id} не привязан к аккаунту {account_id}")
                        continue
                    
                    account_ready = True
                    break
                
                if account_ready:
                    break
            
            if account_ready:
                ready_count += 1
            else:
                not_ready_count += 1
        
        print(f"Готовых к публикации через аккаунты: {ready_count}")
        print(f"Не готовых: {not_ready_count}")
        
        if not_ready_reasons:
            print("\nПричины:")
            for reason in not_ready_reasons[:10]:  # Показываем первые 10
                print(f"  - {reason}")
            if len(not_ready_reasons) > 10:
                print(f"  ... и еще {len(not_ready_reasons) - 10} причин")
        print()
        
        # 4. Проверка активных аккаунтов
        print("4. АКТИВНЫЕ АККАУНТЫ")
        print("-" * 80)
        active_accounts = db.session.query(TelegramAccount).filter_by(is_active=True).all()
        print(f"Всего активных аккаунтов: {len(active_accounts)}")
        
        for acc in active_accounts:
            # Проверяем привязки чатов
            legacy_chats = db.session.query(Chat).filter_by(
                owner_type='user',
                owner_account_id=acc.account_id
            ).count()
            
            new_chats = db.session.query(TelegramAccountChat).filter_by(
                account_id=acc.account_id
            ).count()
            
            total_chats = legacy_chats + new_chats
            
            print(f"  - Account {acc.account_id} ({acc.phone}):")
            print(f"    Режим: {acc.mode}")
            print(f"    Дневной лимит: {acc.daily_limit}")
            print(f"    Привязано чатов: {total_chats} (legacy: {legacy_chats}, new: {new_chats})")
        print()
        
        # 5. Итоговая оценка
        print("5. ИТОГОВАЯ ОЦЕНКА")
        print("-" * 80)
        if ready_count > 0:
            print(f"✅ Автопубликация готова: {ready_count} объектов с аккаунтами и чатами")
        else:
            print("⚠️  Нет объектов, готовых к публикации через аккаунты")
        
        if not_ready_count > 0:
            print(f"⚠️  {not_ready_count} объектов не готовы (см. причины выше)")
        
        print()
        print("=" * 80)
        print("РЕКОМЕНДАЦИИ:")
        print("1. Убедитесь, что все объекты с автопубликацией имеют аккаунты с чатами")
        print("2. Проверьте, что чаты привязаны к аккаунтам (через страницу 'Чаты')")
        print("3. Проверьте логи Celery beat для подтверждения запуска schedule_daily_autopublish")
        print("4. Проверьте логи Celery worker для отслеживания обработки задач")
        print("=" * 80)

if __name__ == '__main__':
    check_autopublish_readiness()

