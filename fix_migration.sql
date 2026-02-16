-- Проверка и исправление версии миграции
-- Если таблица chat_subscription_tasks существует, но версия не обновлена

-- Проверяем текущую версию
SELECT version_num FROM alembic_version;

-- Если таблица chat_subscription_tasks существует, но версия не add_chat_subscription_task,
-- нужно обновить версию вручную:
-- UPDATE alembic_version SET version_num = 'add_chat_subscription_task';

-- Затем можно применить оставшиеся миграции:
-- alembic upgrade add_subscription_chat_links
-- alembic upgrade merge_chat_subscription_and_chat_group

