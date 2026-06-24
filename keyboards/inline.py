from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админа."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Пользователи", callback_data="users"),
                InlineKeyboardButton(text="🚫 Заблокированные", callback_data="banned"),
            ]
        ]
    )
    return kb


def user_page_keyboard(page: int, total_pages: int, is_banned: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для навигации по пользователям."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    nav_buttons = []
    if page > 1:
        callback = f"page_ban_{page - 1}" if is_banned else f"page_{page - 1}"
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=callback))
    
    if page < total_pages:
        callback = f"page_ban_{page + 1}" if is_banned else f"page_{page + 1}"
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=callback))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)
    
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")
    ])
    
    return kb


def user_action_keyboard(user_id: int, is_banned: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для действий с пользователем."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    if is_banned:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"unban_user_{user_id}")
        ])
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="page_ban_1")
        ])
    else:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="🗑️ Удалить и заблокировать", callback_data=f"delete_user_{user_id}")
        ])
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="page_1")
        ])
    
    return kb


def delete_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для удаления пользователей."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"delete_page_{page - 1}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"delete_page_{page + 1}"))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)
    
    return kb


def confirm_keyboard(user_id: int, action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{action}_yes_{user_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{action}_no_{user_id}"),
            ]
        ]
    )
    return kb


def unban_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения разблокировки."""
    return confirm_keyboard(user_id, "unban")


def delete_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления."""
    return confirm_keyboard(user_id, "delete")