#!/usr/bin/env python3
"""
Скрипт для сброса застрявших задач автопубликации от имени аккаунтов

Использование в Docker:
docker exec -it realty_web python scripts/reset_stuck_account_queues.py
"""
import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from app.database import db
from app.models.account_publication_queue import AccountPublicationQueue

def reset_stuck_queues():
    """Сброс застрявших задач в статусе 'processing'"""
    
    with app.app_context():
        print("=" * 80)
        print("СБРОС ЗАСТРЯВШИХ ЗАДАЧ АВТОПУБЛИКАЦИИ ОТ ИМЕНИ АККАУНТОВ")
        print("=" * 80)
        print()
        
        now = datetime.utcnow()
        stuck_threshold = now - timedelta(minutes=5)
        
        print(f"Текущее время UTC: {now}")
        print(f"Порог для застрявших задач: {stuck_threshold} (более 5 минут)")
        print()
        
        # Находим застрявшие задачи
        stuck_queues = db.session.query(AccountPublicationQueue).filter(
            AccountPublicationQueue.status == 'processing',
            AccountPublicationQueue.started_at < stuck_threshold
        ).all()
        
        print(f"Найдено застрявших задач: {len(stuck_queues)}")
        print()
        
        if not stuck_queues:
            print("Застрявших задач не найдено.")
            return
        
        print("Застрявшие задачи:")
        for q in stuck_queues:
            print(f"  - Queue {q.queue_id}:")
            print(f"    Объект: {q.object_id}")
            print(f"    Аккаунт: {q.account_id}")
            print(f"    Чат: {q.chat_id}")
            print(f"    Начато: {q.started_at}")
            print(f"    Прошло времени: {now - q.started_at}")
            print(f"    Попыток: {q.attempts}")
            print()
        
        # Подтверждение
        response = input(f"Сбросить {len(stuck_queues)} задач в статус 'pending'? (yes/no): ")
        if response.lower() != 'yes':
            print("Отменено.")
            return
        
        # Сбрасываем задачи
        reset_count = 0
        failed_count = 0
        
        for stuck_queue in stuck_queues:
            try:
                stuck_queue.status = 'pending'
                stuck_queue.attempts += 1
                if stuck_queue.attempts >= 3:
                    stuck_queue.status = 'failed'
                    stuck_queue.error_message = 'Task timeout - exceeded soft time limit'
                    failed_count += 1
                else:
                    reset_count += 1
                db.session.commit()
                print(f"✅ Queue {stuck_queue.queue_id}: {'сброшена' if reset_count > 0 else 'помечена как failed'}")
            except Exception as e:
                print(f"❌ Ошибка при сбросе queue {stuck_queue.queue_id}: {e}")
                db.session.rollback()
        
        print()
        print("=" * 80)
        print(f"Результат:")
        print(f"  - Сброшено в 'pending': {reset_count}")
        print(f"  - Помечено как 'failed': {failed_count}")
        print("=" * 80)

if __name__ == '__main__':
    reset_stuck_queues()

