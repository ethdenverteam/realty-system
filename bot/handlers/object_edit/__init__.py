"""
Object editing handlers package
Логика: объединение всех handlers для редактирования объектов
"""
# Импортируем все handlers и константы
from bot.handlers.object_edit.handlers_edit_basic import (
    delete_preview_and_menu,
    back_to_preview_handler,
    edit_price_handler,
    edit_price_input,
    edit_area_handler,
    edit_area_input,
    edit_floor_handler,
    edit_floor_input,
    edit_comment_handler,
    edit_comment_input,
    edit_residential_complex_handler,
    residential_complex_input,
    edit_renovation_handler,
    renovation_selected,
    OBJECT_WAITING_EDIT_ROOMS,
    OBJECT_WAITING_EDIT_PRICE,
    OBJECT_WAITING_EDIT_AREA,
    OBJECT_WAITING_EDIT_FLOOR,
    OBJECT_WAITING_EDIT_COMMENT,
    OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX,
    OBJECT_PREVIEW_MENU,
)

from bot.handlers.object_edit.handlers_edit_location import (
    edit_address_handler,
    address_input,
    edit_rooms_handler,
    edit_rooms_selected,
    edit_district_handler,
    edit_district_selected,
    add_district_handler,
    add_district_selected,
    OBJECT_WAITING_EDIT_DISTRICT,
    OBJECT_WAITING_ADD_DISTRICT,
)

from bot.handlers.object_edit.handlers_edit_contacts import (
    edit_contacts_handler,
    contacts_input,
    contact_name_input,
    phone_from_settings_handler,
    phone_custom_handler,
    set_contact_name_handler,
    toggle_username_handler,
)

from bot.handlers.object_edit.handlers_edit_media_delete import (
    add_media_handler,
    object_media_received,
    skip_media,
    edit_object_from_list,
    delete_object_handler,
    confirm_delete_object_handler,
)

__all__ = [
    # Basic
    'delete_preview_and_menu',
    'back_to_preview_handler',
    'edit_price_handler',
    'edit_price_input',
    'edit_area_handler',
    'edit_area_input',
    'edit_floor_handler',
    'edit_floor_input',
    'edit_comment_handler',
    'edit_comment_input',
    'edit_residential_complex_handler',
    'residential_complex_input',
    'edit_renovation_handler',
    'renovation_selected',
    # Location
    'edit_address_handler',
    'address_input',
    'edit_rooms_handler',
    'edit_rooms_selected',
    'edit_district_handler',
    'edit_district_selected',
    'add_district_handler',
    'add_district_selected',
    # Contacts
    'edit_contacts_handler',
    'contacts_input',
    'contact_name_input',
    'phone_from_settings_handler',
    'phone_custom_handler',
    'set_contact_name_handler',
    'toggle_username_handler',
    # Media & Delete
    'add_media_handler',
    'object_media_received',
    'skip_media',
    'edit_object_from_list',
    'delete_object_handler',
    'confirm_delete_object_handler',
    # Constants
    'OBJECT_WAITING_EDIT_ROOMS',
    'OBJECT_WAITING_EDIT_DISTRICT',
    'OBJECT_WAITING_EDIT_PRICE',
    'OBJECT_WAITING_ADD_DISTRICT',
    'OBJECT_WAITING_EDIT_AREA',
    'OBJECT_WAITING_EDIT_FLOOR',
    'OBJECT_WAITING_EDIT_COMMENT',
    'OBJECT_WAITING_EDIT_RESIDENTIAL_COMPLEX',
    'OBJECT_PREVIEW_MENU',
]

