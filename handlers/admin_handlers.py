from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from utils import check_admin, db
from keyboards import user_page_keyboard
from config import USERS_PER_PAGE
from logger_config import logger

admin_commands_router = Router()


async def show_users_page(chat_id: int, users: list, page: int, message_id: int = None, is_banned: bool = False):
    """Отправить или отредактировать страницу с пользователями."""
    from aiogram import Bot
    from keyboards import user_page_keyboard
    
    start = (page - 1) * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    if not page_users:
        return

    keyboard = user_page_keyboard(page, total_pages, is_banned)
    
    # Добавляем кнопки пользователей
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for u in page_users:
        callback = f"user_banned_{u[0]}" if is_banned else f"user_{u[0]}"
        kb.inline_keyboard.append([InlineKeyboardButton(text=u[1], callback_data=callback)])
    
    # Добавляем навигацию
    nav_buttons = []
    if page > 1:
        callback = f"page_ban_{page - 1}" if is_banned else f"page_{page - 1}"
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=callback))
    
    if page < total_pages:
        callback = f"page_ban_{page + 1}" if is_banned else f"page_{page + 1}"
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=callback))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")])
    
    text = "🚫 Чёрный список" if is_banned else "👥 Зарегистрированные пользователи"
    
    return kb, text


@admin_commands_router.message(Command("statistic"))
@check_admin
async def cmd_statistic(message: Message):
    """Показать статистику пользователей."""
    users = db.get_all_users()
    
    if not users:
        await message.answer("Нет зарегистрированных пользователей")
        return
    
    kb, text = await show_users_page(message.chat.id, users, 1)
    await message.answer(text, reply_markup=kb)


@admin_commands_router.message(Command("ban"))
@check_admin
async def cmd_ban(message: Message):
    """Команда /ban <user_id>."""
    parts = message.text.split()
    
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Укажите корректный ID: /ban <user_id>")
        return

    user_id = int(parts[1])
    
    if db.ban_exist(user_id):
        await message.answer("❌ Пользователь уже заблокирован")
        return

    username = db.get_user_name(user_id) or "Неизвестный пользователь"
    db.user_ban(user_id, username, True)
    await message.answer(f"✅ Пользователь {username} заблокирован!")


@admin_commands_router.message(Command("unban"))
@check_admin
async def cmd_unban(message: Message):
    """Команда /unban <user_id>."""
    parts = message.text.split()
    
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Укажите корректный ID: /unban <user_id>")
        return

    user_id = int(parts[1])
    
    if not db.ban_exist(user_id):
        await message.answer("❌ Пользователь не был заблокирован")
        return

    db.user_unban(user_id)
    username = db.get_user_name(user_id) or str(user_id)
    await message.answer(f"✅ Пользователь {username} разблокирован!")


@admin_commands_router.message(Command("delete"))
@check_admin
async def cmd_delete(message: Message):
    """Показать страницу удаления пользователей."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    users = db.get_all_users()
    if not users:
        await message.answer("Нет зарегистрированных пользователей")
        return

    # Показываем первую страницу удаления
    await show_delete_page(message.chat.id, users, 1)


async def show_delete_page(chat_id: int, users: list, page: int, message_id: int = None):
    """Показать страницу удаления пользователей."""
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    start = (page - 1) * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for u in page_users:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"🗑️ {u[1]}", callback_data=f"confirm_delete_{u[0]}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"delete_page_{page - 1}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"delete_page_{page + 1}"))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)

    return kb, "Выберите кого хотите удалить"