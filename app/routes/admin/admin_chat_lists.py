"""
Admin chat lists management routes
Логика: управление списками чатов для подписки (ChatGroup с purpose='subscription')
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models.user import User
from app.models.chat import Chat
from app.models.chat_group import ChatGroup
from app.models.telegram_account import TelegramAccount
from app.utils.decorators import jwt_required, role_required
from app.utils.logger import log_action, log_error
import logging

admin_chat_lists_bp = Blueprint('admin_chat_lists', __name__)
logger = logging.getLogger(__name__)


@admin_chat_lists_bp.route('/dashboard/chat-lists', methods=['GET'])
@jwt_required
@role_required('admin')
def admin_chat_lists(current_user):
    """Получить все списки чатов (ChatGroup) для подписок с расшифровкой чатов"""
    try:
        groups = ChatGroup.query.filter_by(purpose='subscription').order_by(ChatGroup.created_at.desc()).all()
        users_by_id = {u.user_id: u for u in User.query.filter(
            User.user_id.in_([g.user_id for g in groups])
        ).all()} if groups else {}

        result = []
        for group in groups:
            group_data = group.to_dict()
            # Добавляем информацию о пользователе
            user = users_by_id.get(group.user_id)
            group_data['user_name'] = user.username if user else None

            # Получаем чаты из chat_ids (для обратной совместимости)
            chat_ids = group.chat_ids or []
            chats_by_id = {}
            if chat_ids:
                chats = Chat.query.filter(Chat.chat_id.in_(chat_ids)).all()
                chats_by_id = {chat.chat_id: chat for chat in chats}
            else:
                chats = []

            # Получаем данные из chat_links (новый формат с названиями)
            chat_links_list = group.get_chat_links_list()
            
            chat_dicts = []
            # Сначала добавляем чаты из БД
            for chat in chats:
                chat_info = {
                    'chat_id': chat.chat_id,
                    'telegram_chat_id': chat.telegram_chat_id,
                    'title': chat.title,
                    'owner_type': chat.owner_type,
                    'account_id': chat.owner_account_id,
                }
                account_phone = None
                if chat.owner_account_id:
                    acc = TelegramAccount.query.get(chat.owner_account_id)
                    if acc:
                        account_phone = acc.phone
                chat_info['account_phone'] = account_phone
                chat_dicts.append(chat_info)
            
            # Затем добавляем чаты из chat_links, которых нет в БД (еще не подписаны)
            for link_item in chat_links_list:
                link = link_item.get('link', '')
                telegram_chat_id = link_item.get('telegram_chat_id')
                title = link_item.get('title')
                
                # Ищем, есть ли уже этот чат в chat_dicts
                existing_chat = None
                if telegram_chat_id:
                    for chat_dict in chat_dicts:
                        if chat_dict.get('telegram_chat_id') == telegram_chat_id:
                            existing_chat = chat_dict
                            break
                
                # Если чат не найден в БД, но есть данные из chat_links - добавляем
                if not existing_chat:
                    chat_dicts.append({
                        'chat_id': None,  # Еще не создан в БД
                        'telegram_chat_id': telegram_chat_id or None,
                        'title': title or None,
                        'owner_type': 'user',
                        'account_id': None,
                        'account_phone': None,
                        'link': link,  # Сохраняем ссылку для отображения
                    })

            group_data['chats'] = chat_dicts
            result.append(group_data)

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting admin chat lists: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_chat_lists_bp.route('/dashboard/chat-lists', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_create_chat_list(current_user):
    """
    Создать новый список чатов для подписки (ChatGroup с purpose='subscription')
    Body: {user_id: int, name: str, links: str}
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    name = (data.get('name') or '').strip()
    links_text = (data.get('links') or '').strip()

    if not user_id:
        return jsonify({'error': 'user_id обязателен'}), 400
    if not name:
        return jsonify({'error': 'Название списка обязательно'}), 400
    if not links_text:
        return jsonify({'error': 'Список ссылок не может быть пустым'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    try:
        # Парсим ссылки
        links = [line.strip() for line in links_text.split('\n') if line.strip()]
        links = [link for link in links if link.startswith('https://t.me/') or link.startswith('http://t.me/')]

        if not links:
            return jsonify({'error': 'Не найдено валидных ссылок (должны начинаться с https://t.me/)'}), 400

        chat_ids = []
        for link in links:
            temp_chat_id = None
            if link.startswith('https://t.me/+') or link.startswith('http://t.me/+'):
                hash_part = link.split('+')[-1]
                temp_chat_id = f"invite_{user.user_id}_{hash_part}"
            else:
                username = link.split('/')[-1].replace('@', '')
                temp_chat_id = f"public_{user.user_id}_{username}"

            chat = Chat.query.filter_by(telegram_chat_id=temp_chat_id).first()
            if not chat:
                chat = Chat(
                    telegram_chat_id=temp_chat_id,
                    title=f"Chat {temp_chat_id}",
                    type='group',
                    owner_type='user',
                    owner_account_id=None,
                    is_active=False,
                )
                db.session.add(chat)
                db.session.flush()

            chat_ids.append(chat.chat_id)

        # Сохраняем ссылки в новом формате
        links_list = [{"link": link, "telegram_chat_id": None, "title": None} for link in links]
        group = ChatGroup(
            user_id=user.user_id,
            name=name,
            chat_ids=chat_ids,
            chat_links=links_list,
            purpose='subscription',
        )
        db.session.add(group)
        db.session.commit()

        log_action(
            user_id=current_user.user_id,
            action='admin_create_chat_list',
            details={'group_id': group.group_id, 'user_id': user.user_id, 'name': name, 'chats_count': len(chat_ids)},
        )

        return jsonify(group.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating admin chat list: {e}", exc_info=True)
        log_error(e, 'admin_create_chat_list', current_user.user_id, {'user_id': user_id, 'name': name})
        return jsonify({'error': str(e)}), 500


@admin_chat_lists_bp.route('/dashboard/chat-lists/<int:group_id>', methods=['DELETE'])
@jwt_required
@role_required('admin')
def admin_delete_chat_list(current_user, group_id):
    """Удалить список чатов (ChatGroup purpose='subscription')"""
    try:
        group = ChatGroup.query.filter_by(group_id=group_id, purpose='subscription').first()
        if not group:
            return jsonify({'error': 'Список не найден'}), 404

        db.session.delete(group)
        db.session.commit()

        log_action(
            user_id=current_user.user_id,
            action='admin_delete_chat_list',
            details={'group_id': group_id, 'user_id': group.user_id},
        )

        return jsonify({'message': 'Список удален'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting admin chat list: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_chat_lists_bp.route('/dashboard/chat-lists/<int:group_id>/chats', methods=['POST'])
@jwt_required
@role_required('admin')
def admin_add_chat_to_list(current_user, group_id):
    """
    Добавить чат в список по ссылке
    Body: {link: str}
    """
    data = request.get_json() or {}
    link = (data.get('link') or '').strip()

    if not link:
        return jsonify({'error': 'link обязателен'}), 400

    group = ChatGroup.query.filter_by(group_id=group_id, purpose='subscription').first()
    if not group:
        return jsonify({'error': 'Список не найден'}), 404

    try:
        if not (link.startswith('https://t.me/') or link.startswith('http://t.me/')):
            return jsonify({'error': 'Ссылка должна начинаться с https://t.me/ или http://t.me/'}), 400

        chat_ids = group.chat_ids or []

        # Строим временный telegram_chat_id так же, как в create_chat_group
        if link.startswith('https://t.me/+') or link.startswith('http://t.me/+'):
            hash_part = link.split('+')[-1]
            temp_chat_id = f"invite_{group.user_id}_{hash_part}"
        else:
            username = link.split('/')[-1].replace('@', '')
            temp_chat_id = f"public_{group.user_id}_{username}"

        chat = Chat.query.filter_by(telegram_chat_id=temp_chat_id).first()
        if not chat:
            chat = Chat(
                telegram_chat_id=temp_chat_id,
                title=f"Chat {temp_chat_id}",
                type='group',
                owner_type='user',
                owner_account_id=None,
                is_active=False,
            )
            db.session.add(chat)
            db.session.flush()

        if chat.chat_id not in chat_ids:
            chat_ids.append(chat.chat_id)
        group.chat_ids = chat_ids

        # Обновляем ссылки в новом формате
        links_list = group.get_chat_links_list()
        # Проверяем, нет ли уже такой ссылки
        link_exists = any(item.get('link') == link for item in links_list)
        if not link_exists:
            links_list.append({"link": link, "telegram_chat_id": None, "title": None})
        group.set_chat_links_list(links_list)

        db.session.commit()

        log_action(
            user_id=current_user.user_id,
            action='admin_add_chat_to_list',
            details={'group_id': group_id, 'chat_id': chat.chat_id, 'link': link},
        )

        return jsonify(group.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding chat to admin chat list: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_chat_lists_bp.route('/dashboard/chat-lists/<int:group_id>/public', methods=['PUT'])
@jwt_required
@role_required('admin')
def admin_set_chat_list_public(current_user, group_id):
    """
    Установить/снять публичность списка чатов.
    Body: {is_public: bool}
    """
    data = request.get_json() or {}
    is_public = bool(data.get('is_public', False))

    try:
        group = ChatGroup.query.filter_by(group_id=group_id, purpose='subscription').first()
        if not group:
            return jsonify({'error': 'Список не найден'}), 404

        previous = getattr(group, 'is_public', False)
        group.is_public = is_public
        db.session.commit()

        log_action(
            user_id=current_user.user_id,
            action='admin_set_chat_list_public',
            details={'group_id': group_id, 'previous_is_public': previous, 'is_public': is_public},
        )

        return jsonify(group.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting chat list public flag: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_chat_lists_bp.route('/dashboard/chat-lists/<int:group_id>/chats/<int:chat_id>', methods=['DELETE'])
@jwt_required
@role_required('admin')
def admin_remove_chat_from_list(current_user, group_id, chat_id):
    """Удалить чат из списка (не удаляя сам чат из БД)"""
    try:
        group = ChatGroup.query.filter_by(group_id=group_id, purpose='subscription').first()
        if not group:
            return jsonify({'error': 'Список не найден'}), 404

        chat_ids = group.chat_ids or []
        if chat_id not in chat_ids:
            return jsonify({'error': 'Чат не входит в этот список'}), 400

        chat_ids = [cid for cid in chat_ids if cid != chat_id]
        group.chat_ids = chat_ids
        db.session.commit()

        log_action(
            user_id=current_user.user_id,
            action='admin_remove_chat_from_list',
            details={'group_id': group_id, 'chat_id': chat_id},
        )

        return jsonify(group.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing chat from admin chat list: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

