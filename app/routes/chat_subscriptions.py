"""
Chat subscriptions routes - управление подписками на списки чатов
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.chat import Chat
from app.models.chat_group import ChatGroup
from app.models.chat_subscription_task import ChatSubscriptionTask
from app.models.telegram_account import TelegramAccount
from app.utils.decorators import jwt_required
from app.utils.logger import log_action, log_error
from datetime import datetime, timedelta
import logging
import re

chat_subscriptions_bp = Blueprint('chat_subscriptions', __name__)
logger = logging.getLogger(__name__)


@chat_subscriptions_bp.route('/groups', methods=['POST'])
@jwt_required
def create_chat_group(current_user):
    """
    Создать список чатов из ссылок
    Body: {name: str, links: str} - links это многострочный текст со ссылками
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        links_text = data.get('links', '').strip()
        
        if not name:
            return jsonify({'error': 'Название списка обязательно'}), 400
        
        if not links_text:
            return jsonify({'error': 'Список ссылок не может быть пустым'}), 400
        
        # Парсим ссылки из текста (каждая строка - ссылка)
        links = [line.strip() for line in links_text.split('\n') if line.strip()]
        links = [link for link in links if link.startswith('https://t.me/') or link.startswith('http://t.me/')]
        
        if not links:
            return jsonify({'error': 'Не найдено валидных ссылок (должны начинаться с https://t.me/)'}), 400
        
        # Создаем или обновляем чаты в БД и собираем chat_ids
        chat_ids = []
        for link in links:
            # Проверяем, существует ли чат с такой ссылкой
            # Для этого нужно хранить ссылку в Chat - но у нас нет такого поля
            # Пока создаем чаты без telegram_chat_id (будет заполнено после подписки)
            # Или используем ссылку как временный идентификатор
            
            # Парсим ссылку для получения временного ID
            # Для invite ссылок: https://t.me/+Poqjzr81Y3MzMTk6 -> используем hash как временный ID
            # Для публичных: https://t.me/username -> используем username
            
            temp_chat_id = None
            if link.startswith('https://t.me/+') or link.startswith('http://t.me/+'):
                # Invite ссылка - используем hash как временный идентификатор
                hash_part = link.split('+')[-1]
                # Добавляем user_id для уникальности (чтобы разные пользователи могли создавать группы с одинаковыми ссылками)
                temp_chat_id = f"invite_{current_user.user_id}_{hash_part}"
            else:
                # Публичный чат
                username = link.split('/')[-1].replace('@', '')
                # Добавляем user_id для уникальности
                temp_chat_id = f"public_{current_user.user_id}_{username}"
            
            # Ищем или создаем чат
            # Используем telegram_chat_id для хранения временного идентификатора до подписки
            chat = Chat.query.filter_by(telegram_chat_id=temp_chat_id).first()
            
            if not chat:
                # Создаем новый чат (пока без реального telegram_chat_id)
                chat = Chat(
                    telegram_chat_id=temp_chat_id,  # Временный ID, будет заменен после подписки
                    title=f"Chat {temp_chat_id}",  # Временное название
                    type='group',  # По умолчанию
                    owner_type='user',
                    owner_account_id=None,  # Будет заполнено после подписки
                    is_active=False,  # Не активен до подписки
                )
                try:
                    db.session.add(chat)
                    db.session.flush()  # Получаем chat_id
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error creating chat for link {link}: {e}", exc_info=True)
                    # Если ошибка уникальности - пробуем найти существующий
                    chat = Chat.query.filter_by(telegram_chat_id=temp_chat_id).first()
                    if not chat:
                        raise
            
            chat_ids.append(chat.chat_id)
        
        # Создаем или обновляем ChatGroup
        # Проверяем, есть ли уже группа с таким названием у пользователя
        existing_group = ChatGroup.query.filter_by(user_id=current_user.user_id, name=name).first()
        
        if existing_group:
            # Обновляем существующую группу
            existing_group.chat_ids = chat_ids
            existing_group.chat_links = links  # Сохраняем исходные ссылки
            existing_group.updated_at = datetime.utcnow()
            db.session.commit()
            
            log_action(
                user_id=current_user.user_id,
                action='update_chat_group',
                details={'group_id': existing_group.group_id, 'name': name, 'chats_count': len(chat_ids)}
            )
            
            return jsonify(existing_group.to_dict()), 200
        else:
            # Создаем новую группу
            group = ChatGroup(
                user_id=current_user.user_id,
                name=name,
                chat_ids=chat_ids,
                chat_links=links,  # Сохраняем исходные ссылки
            )
            db.session.add(group)
            db.session.commit()
            
            log_action(
                user_id=current_user.user_id,
                action='create_chat_group',
                details={'group_id': group.group_id, 'name': name, 'chats_count': len(chat_ids)}
            )
            
            return jsonify(group.to_dict()), 201
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating chat group: {e}", exc_info=True)
        log_error(
            error=e,
            action='create_chat_group',
            user_id=current_user.user_id if current_user else None,
        )
        return jsonify({'error': str(e)}), 500


@chat_subscriptions_bp.route('/groups', methods=['GET'])
@jwt_required
def list_chat_groups(current_user):
    """Получить список групп чатов пользователя"""
    try:
        groups = ChatGroup.query.filter_by(user_id=current_user.user_id).all()
        return jsonify([group.to_dict() for group in groups]), 200
    except Exception as e:
        logger.error(f"Error listing chat groups: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_subscriptions_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@jwt_required
def delete_chat_group(current_user, group_id):
    """Удалить группу чатов"""
    try:
        group = ChatGroup.query.filter_by(group_id=group_id, user_id=current_user.user_id).first()
        if not group:
            return jsonify({'error': 'Группа не найдена'}), 404
        
        db.session.delete(group)
        db.session.commit()
        
        log_action(
            user_id=current_user.user_id,
            action='delete_chat_group',
            details={'group_id': group_id}
        )
        
        return jsonify({'message': 'Группа удалена'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting chat group: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_subscriptions_bp.route('/tasks', methods=['POST'])
@jwt_required
def start_subscription(current_user):
    """
    Запустить подписку на список чатов
    Body: {account_id: int, group_id: int}
    """
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        group_id = data.get('group_id')
        
        if not account_id or not group_id:
            return jsonify({'error': 'account_id и group_id обязательны'}), 400
        
        # Проверяем, что аккаунт принадлежит пользователю
        account = TelegramAccount.query.filter_by(account_id=account_id, owner_id=current_user.user_id).first()
        if not account:
            return jsonify({'error': 'Аккаунт не найден'}), 404
        
        # Проверяем, что группа принадлежит пользователю
        group = ChatGroup.query.filter_by(group_id=group_id, user_id=current_user.user_id).first()
        if not group:
            return jsonify({'error': 'Группа не найдена'}), 404
        
        # Проверяем, нет ли уже активной задачи подписки для этого аккаунта
        active_task = ChatSubscriptionTask.query.filter_by(
            account_id=account_id,
            status='processing'
        ).first()
        
        if active_task:
            return jsonify({'error': 'У этого аккаунта уже есть активная задача подписки'}), 400
        
        # Получаем ссылки на чаты из группы
        chat_links = group.chat_links or []
        
        # Если ссылок нет в группе, пытаемся восстановить из chat_ids
        if not chat_links:
            for chat_id in group.chat_ids:
                chat = Chat.query.get(chat_id)
                if chat:
                    # Восстанавливаем ссылку из telegram_chat_id
                    if chat.telegram_chat_id.startswith('invite_'):
                        hash_part = chat.telegram_chat_id.replace('invite_', '')
                        chat_links.append(f"https://t.me/+{hash_part}")
                    elif chat.telegram_chat_id.startswith('public_'):
                        username = chat.telegram_chat_id.replace('public_', '')
                        chat_links.append(f"https://t.me/{username}")
        
        if not chat_links:
            return jsonify({'error': 'Не найдено ссылок на чаты в группе'}), 400
        
        # Создаем задачу подписки
        task = ChatSubscriptionTask(
            user_id=current_user.user_id,
            account_id=account_id,
            group_id=group_id,
            status='pending',
            current_index=0,
            total_chats=len(chat_links),
            successful_count=0,
            flood_count=0,
            chat_links=chat_links,
        )
        db.session.add(task)
        db.session.commit()
        
        # Запускаем Celery задачу
        from workers.tasks import subscribe_to_chats_task
        subscribe_to_chats_task.delay(task.task_id)
        
        log_action(
            user_id=current_user.user_id,
            action='start_chat_subscription',
            details={'task_id': task.task_id, 'account_id': account_id, 'group_id': group_id, 'chats_count': len(chat_links)}
        )
        
        return jsonify(task.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting subscription: {e}", exc_info=True)
        log_error(
            error=e,
            action='start_chat_subscription',
            user_id=current_user.user_id if current_user else None,
        )
        return jsonify({'error': str(e)}), 500


@chat_subscriptions_bp.route('/tasks', methods=['GET'])
@jwt_required
def list_subscription_tasks(current_user):
    """Получить список задач подписки пользователя"""
    try:
        tasks = ChatSubscriptionTask.query.filter_by(user_id=current_user.user_id).order_by(ChatSubscriptionTask.created_at.desc()).all()
        return jsonify([task.to_dict() for task in tasks]), 200
    except Exception as e:
        logger.error(f"Error listing subscription tasks: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_subscriptions_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required
def get_subscription_task(current_user, task_id):
    """Получить задачу подписки"""
    try:
        task = ChatSubscriptionTask.query.filter_by(task_id=task_id, user_id=current_user.user_id).first()
        if not task:
            return jsonify({'error': 'Задача не найдена'}), 404
        
        return jsonify(task.to_dict()), 200
    except Exception as e:
        logger.error(f"Error getting subscription task: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@chat_subscriptions_bp.route('/tasks/<int:task_id>/continue', methods=['POST'])
@jwt_required
def continue_subscription(current_user, task_id):
    """Продолжить подписку после flood"""
    try:
        task = ChatSubscriptionTask.query.filter_by(task_id=task_id, user_id=current_user.user_id).first()
        if not task:
            return jsonify({'error': 'Задача не найдена'}), 404
        
        if task.status != 'flood_wait':
            return jsonify({'error': 'Задача не в статусе flood_wait'}), 400
        
        # Проверяем, прошло ли время flood
        if task.flood_wait_until and task.flood_wait_until > datetime.utcnow():
            wait_seconds = int((task.flood_wait_until - datetime.utcnow()).total_seconds())
            return jsonify({'error': f'Нужно подождать еще {wait_seconds} секунд'}), 400
        
        # Обновляем статус и запускаем задачу
        task.status = 'pending'
        task.flood_wait_until = None
        db.session.commit()
        
        # Запускаем Celery задачу
        from workers.tasks import subscribe_to_chats_task
        subscribe_to_chats_task.delay(task.task_id)
        
        log_action(
            user_id=current_user.user_id,
            action='continue_chat_subscription',
            details={'task_id': task_id}
        )
        
        return jsonify(task.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error continuing subscription: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

