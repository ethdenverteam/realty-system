#!/usr/bin/env python3
"""
Точечная диагностика жизненного цикла объекта в аккаунтных очередях.

Показывает:
- конфигурацию автопубликации объекта (аккаунты/чаты);
- задачи в account_publication_queues по объекту;
- статус каждой задачи, время, попытки, причину ошибки;
- связанные публикации в PublicationHistory;
- сводку "готово сейчас / в обработке / ошибки".

Использование:
docker exec -it realty_web python scripts/object_account_lifecycle.py ААА060
"""

import os
import sys
from datetime import datetime

from sqlalchemy import func

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from app.database import db
from app.models.account_publication_queue import AccountPublicationQueue
from app.models.autopublish_config import AutopublishConfig
from app.models.chat import Chat
from app.models.object import Object
from app.models.publication_history import PublicationHistory
from app.models.telegram_account import TelegramAccount
from app.utils.time_utils import utc_to_msk


def _fmt_dt(dt: datetime) -> str:
    if not dt:
        return "-"
    return f"UTC {dt} | MSK {utc_to_msk(dt)}"


def _print_config(cfg: AutopublishConfig) -> None:
    print("1) КОНФИГУРАЦИЯ ОБЪЕКТА")
    print("-" * 90)
    if not cfg:
        print("❌ AutopublishConfig не найден")
        print()
        return

    print(f"Config ID: {cfg.config_id}")
    print(f"enabled: {cfg.enabled}")
    print(f"bot_enabled: {cfg.bot_enabled}")
    print(f"created_at: {_fmt_dt(cfg.created_at)}")
    print(f"updated_at: {_fmt_dt(cfg.updated_at)}")

    accounts_cfg = cfg.accounts_config_json if isinstance(cfg.accounts_config_json, dict) else {}
    accounts_list = accounts_cfg.get("accounts", [])
    publication_format = accounts_cfg.get("publication_format", "default")
    print(f"publication_format: {publication_format}")
    print(f"accounts in config: {len(accounts_list)}")

    for acc_entry in accounts_list:
        account_id = acc_entry.get("account_id")
        chat_ids = acc_entry.get("chat_ids", [])
        acc = TelegramAccount.query.get(account_id) if account_id else None
        phone = acc.phone if acc else "NOT_FOUND"
        active = acc.is_active if acc else False
        print(f"  - account_id={account_id}, phone={phone}, active={active}, chats={chat_ids}")
    print()


def _print_queues(object_id: str) -> None:
    print("2) ACCOUNT_PUBLICATION_QUEUES ПО ОБЪЕКТУ")
    print("-" * 90)
    now = datetime.utcnow()

    queues = (
        db.session.query(AccountPublicationQueue)
        .filter(AccountPublicationQueue.object_id == object_id)
        .order_by(AccountPublicationQueue.created_at.asc(), AccountPublicationQueue.queue_id.asc())
        .all()
    )

    if not queues:
        print("❌ Задач в account_publication_queues для объекта нет")
        print()
        return

    print(f"Всего задач: {len(queues)}")

    by_status = {}
    for q in queues:
        by_status[q.status] = by_status.get(q.status, 0) + 1
    print(f"Статусы: {by_status}")

    ready_now = sum(1 for q in queues if q.status == "pending" and q.scheduled_time and q.scheduled_time <= now)
    print(f"Готово к обработке сейчас (pending & scheduled_time<=now): {ready_now}")
    print()

    for q in queues:
        acc = TelegramAccount.query.get(q.account_id) if q.account_id else None
        chat = Chat.query.get(q.chat_id) if q.chat_id else None
        phone = acc.phone if acc else "NOT_FOUND"
        title = chat.title if chat else "NOT_FOUND"
        print(f"Queue {q.queue_id}")
        print(f"  status: {q.status}")
        print(f"  account: {q.account_id} ({phone})")
        print(f"  chat: {q.chat_id} ({title})")
        print(f"  scheduled: {_fmt_dt(q.scheduled_time)}")
        print(f"  created: {_fmt_dt(q.created_at)}")
        print(f"  started: {_fmt_dt(q.started_at)}")
        print(f"  completed: {_fmt_dt(q.completed_at)}")
        print(f"  attempts: {q.attempts}")
        print(f"  message_id: {q.message_id or '-'}")
        print(f"  error_message: {q.error_message or '-'}")
        if q.status == "processing" and q.started_at:
            age = now - q.started_at
            print(f"  processing_age: {age}")
        print()


def _print_history(object_id: str) -> None:
    print("3) ИСТОРИЯ ПУБЛИКАЦИЙ ПО ОБЪЕКТУ (ACCOUNT)")
    print("-" * 90)
    rows = (
        db.session.query(PublicationHistory)
        .filter(
            PublicationHistory.object_id == object_id,
            PublicationHistory.account_id.isnot(None),
            PublicationHistory.deleted == False,
        )
        .order_by(PublicationHistory.published_at.asc())
        .all()
    )

    if not rows:
        print("Публикаций от имени аккаунтов для объекта пока нет")
        print()
        return

    print(f"Публикаций найдено: {len(rows)}")
    for h in rows:
        acc = TelegramAccount.query.get(h.account_id) if h.account_id else None
        chat = Chat.query.get(h.chat_id) if h.chat_id else None
        phone = acc.phone if acc else "NOT_FOUND"
        title = chat.title if chat else "NOT_FOUND"
        print(
            f"- history_id={h.history_id}, published={_fmt_dt(h.published_at)}, "
            f"account={h.account_id}({phone}), chat={h.chat_id}({title}), message_id={h.message_id}"
        )
    print()


def _print_summary(object_id: str) -> None:
    print("4) ИТОГ")
    print("-" * 90)
    now = datetime.utcnow()
    total = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
        AccountPublicationQueue.object_id == object_id
    ).scalar() or 0
    pending = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
        AccountPublicationQueue.object_id == object_id,
        AccountPublicationQueue.status == "pending",
    ).scalar() or 0
    processing = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
        AccountPublicationQueue.object_id == object_id,
        AccountPublicationQueue.status == "processing",
    ).scalar() or 0
    completed = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
        AccountPublicationQueue.object_id == object_id,
        AccountPublicationQueue.status == "completed",
    ).scalar() or 0
    failed = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
        AccountPublicationQueue.object_id == object_id,
        AccountPublicationQueue.status == "failed",
    ).scalar() or 0
    ready = db.session.query(func.count(AccountPublicationQueue.queue_id)).filter(
        AccountPublicationQueue.object_id == object_id,
        AccountPublicationQueue.status == "pending",
        AccountPublicationQueue.scheduled_time <= now,
    ).scalar() or 0

    print(f"Всего: {total} | pending: {pending} | processing: {processing} | completed: {completed} | failed: {failed}")
    print(f"Готово к немедленной обработке: {ready}")
    if processing > 0:
        print("⚠️ Есть processing-задачи. Если висят >5 минут, их нужно сбросить скриптом reset_stuck_account_queues.py")
    elif ready > 0:
        print("✅ Есть задачи, которые должны быть подхвачены process_account_autopublish")
    elif pending > 0 and ready == 0:
        print("ℹ️ Есть pending, но scheduled_time еще в будущем")
    elif completed > 0:
        print("✅ Публикация для объекта уже проходила")
    else:
        print("ℹ️ По объекту нет активных задач к выполнению")
    print()


def main() -> None:
    object_id = sys.argv[1] if len(sys.argv) > 1 else "ААА060"
    with app.app_context():
        print("=" * 90)
        print("ЖИЗНЕННЫЙ ЦИКЛ ОБЪЕКТА В АККАУНТНЫХ ОЧЕРЕДЯХ")
        print("=" * 90)
        print(f"Объект: {object_id}")
        print(f"Проверка: {_fmt_dt(datetime.utcnow())}")
        print()

        obj = Object.query.filter_by(object_id=object_id).first()
        if not obj:
            print(f"❌ Объект {object_id} не найден")
            return

        print(f"Объект найден: id={obj.object_id}, status={obj.status}, user_id={obj.user_id}")
        print()

        cfg = AutopublishConfig.query.filter_by(object_id=object_id).first()
        _print_config(cfg)
        _print_queues(object_id)
        _print_history(object_id)
        _print_summary(object_id)
        print("=" * 90)


if __name__ == "__main__":
    main()

