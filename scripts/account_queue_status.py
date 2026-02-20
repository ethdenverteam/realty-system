#!/usr/bin/env python3
"""
Оперативный статус аккаунтных очередей автопубликации.

Показывает по каждому аккаунту:
- сколько задач в pending/processing/completed/failed/flood_wait
- сколько публикаций сделано сегодня
- ближайшую задачу и время до нее
- ориентировочное время "освобождения" аккаунта

Использование:
docker exec -it realty_web python scripts/account_queue_status.py
"""

import os
import sys
from datetime import datetime

from sqlalchemy import func

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from app.database import db
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.publication_history import PublicationHistory
from app.models.telegram_account import TelegramAccount
from app.utils.account_publication_utils import get_interval_minutes
from app.utils.time_utils import utc_to_msk


def _fmt_delta(seconds: float) -> str:
    if seconds <= 0:
        return "сейчас"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    hours = minutes // 60
    minutes = minutes % 60
    if hours:
        return f"{hours}ч {minutes}м"
    if minutes:
        return f"{minutes}м {secs}с"
    return f"{secs}с"


def print_account_queue_status() -> None:
    with app.app_context():
        now_utc = datetime.utcnow()
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        accounts = (
            db.session.query(TelegramAccount)
            .filter(TelegramAccount.is_active == True)
            .order_by(TelegramAccount.account_id.asc())
            .all()
        )

        print("=" * 90)
        print("СТАТУС АККАУНТОВ И ОЧЕРЕДЕЙ АВТОПУБЛИКАЦИИ")
        print("=" * 90)
        print(f"UTC: {now_utc}")
        print(f"MSK: {utc_to_msk(now_utc)}")
        print()
        print(f"Активных аккаунтов: {len(accounts)}")
        print()

        for acc in accounts:
            pending = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == "pending",
            ).scalar() or 0

            processing = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == "processing",
            ).scalar() or 0

            completed = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == "completed",
            ).scalar() or 0

            failed = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == "failed",
            ).scalar() or 0

            flood_wait = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == "flood_wait",
            ).scalar() or 0

            today_publications = db.session.query(func.count(PublicationHistory.history_id)).filter(
                PublicationHistory.account_id == acc.account_id,
                PublicationHistory.published_at >= today_start,
                PublicationHistory.deleted == False,
            ).scalar() or 0

            ready_now = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
                AccountPublicationQueue.account_id == acc.account_id,
                AccountPublicationQueue.status == "pending",
                AccountPublicationQueue.scheduled_time <= now_utc,
            ).scalar() or 0

            next_pending = (
                db.session.query(AccountPublicationQueue)
                .filter(
                    AccountPublicationQueue.account_id == acc.account_id,
                    AccountPublicationQueue.status == "pending",
                )
                .order_by(AccountPublicationQueue.scheduled_time.asc())
                .first()
            )

            processing_oldest = (
                db.session.query(AccountPublicationQueue)
                .filter(
                    AccountPublicationQueue.account_id == acc.account_id,
                    AccountPublicationQueue.status == "processing",
                    AccountPublicationQueue.started_at.isnot(None),
                )
                .order_by(AccountPublicationQueue.started_at.asc())
                .first()
            )

            mode_interval = get_interval_minutes(acc.mode, acc.fix_interval_minutes)

            print(f"Account {acc.account_id} ({acc.phone})")
            print(f"  Режим: {acc.mode} (базовый интервал: {mode_interval} мин)")
            print(f"  Лимит сегодня: {today_publications}/{acc.daily_limit}")
            print(f"  Очередь: pending={pending}, processing={processing}, completed={completed}, failed={failed}, flood_wait={flood_wait}")
            print(f"  Готово к отправке сейчас: {ready_now}")

            if processing_oldest and processing_oldest.started_at:
                age_seconds = (now_utc - processing_oldest.started_at).total_seconds()
                print(
                    f"  В работе: queue={processing_oldest.queue_id}, уже {_fmt_delta(age_seconds)}"
                )

            if next_pending:
                wait_seconds = (next_pending.scheduled_time - now_utc).total_seconds()
                print(
                    f"  Следующая задача: queue={next_pending.queue_id}, "
                    f"scheduled_utc={next_pending.scheduled_time}, "
                    f"scheduled_msk={utc_to_msk(next_pending.scheduled_time)}, "
                    f"через {_fmt_delta(wait_seconds)}"
                )
            else:
                print("  Следующая задача: нет pending задач")

            if processing > 0:
                print("  Свободен: после завершения текущей processing-задачи")
            elif next_pending and next_pending.scheduled_time > now_utc:
                free_for = (next_pending.scheduled_time - now_utc).total_seconds()
                print(f"  Свободен сейчас: да, до следующей задачи примерно {_fmt_delta(free_for)}")
            else:
                print("  Свободен сейчас: да")

            if acc.last_error:
                print(f"  Последняя ошибка: {acc.last_error}")
            print()

        print("=" * 90)


if __name__ == "__main__":
    print_account_queue_status()

