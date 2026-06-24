from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import check_admin, db, safe_answer_callback
from config import USERS_PER_PAGE, ADMIN_ID
from logger_config import logger

user_callbacks_router = Router()


def create_user_page_keyboard(page: int, total_pages: int, is_banned: bool = False):
    """Создать клавиатуру для страницы пользователей."""
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
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")])
    
    return kb


async def show_users_page_callback(call: CallbackQuery, users: list, page: int, is_banned: bool = False):
    """Показать страницу пользователей через callback."""
    start = (page - 1) * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    if not page_users and page > 1:
        page = 1
        start = 0
        end = USERS_PER_PAGE
        page_users = users[start:end]

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for u in page_users:
        callback = f"user_banned_{u[0]}" if is_banned else f"user_{u[0]}"
        kb.inline_keyboard.append([InlineKeyboardButton(text=u[1], callback_data=callback)])

    nav_kb = create_user_page_keyboard(page, total_pages, is_banned)
    kb.inline_keyboard.extend(nav_kb.inline_keyboard)
    
    text = "🚫 Чёрный список" if is_banned else "👥 Зарегистрированные пользователи"
    
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await call.message.answer(text, reply_markup=kb)
    
    await safe_answer_callback(call)


@user_callbacks_router.callback_query(F.data.startswith("page_") | F.data.startswith("page_ban_"))
async def cb_page_navigation(call: CallbackQuery):
    """Обработчик навигации по страницам пользователей."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        data = call.data
        
        if data.startswith("page_ban_"):
            page = int(data.split("_")[2])
            users = db.get_banned_users()
            await show_users_page_callback(call, users, page, is_banned=True)
        else:
            page = int(data.split("_")[1])
            users = db.get_all_users()
            await show_users_page_callback(call, users, page, is_banned=False)
    
    except Exception as e:
        logger.error(f"cb_page_navigation error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@user_callbacks_router.callback_query(F.data.startswith("user_"))
async def cb_user_info(call: CallbackQuery):
    """Обработчик для показа информации о пользователе."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        data = call.data
        
        if data.startswith("user_banned_"):
            user_id = int(data.split("_")[2])
            user = db.get_banned_user_by_id(user_id)
            is_banned = True
        else:
            user_id = int(data.split("_")[1])
            user = db.get_user_by_id(user_id)
            is_banned = False

        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return

        await safe_answer_callback(call, user[1])

        if is_banned:
            info = f"🚫 Пользователь заблокирован\n\nID: {user[0]}\nИмя: {user[1]}"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"unban_user_{user[0]}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="page_ban_1")]
            ])
        else:
            info = (
                f"👤 Информация о пользователе\n\n"
                f"Имя: {user[1]}\n"
                f"ID: {user[0]}\n"
                f"Статус: {user[2]}\n"
                f"Пройдено тестов: {user[3]}\n"
                f"✅ Правильных: {user[4]}\n"
                f"❌ Неправильных: {user[5]}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Удалить и заблокировать", callback_data=f"delete_user_{user[0]}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="page_1")]
            ])

        try:
            await call.message.edit_text(info, reply_markup=kb)
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await call.message.answer(info, reply_markup=kb)

    except Exception as e:
        logger.error(f"cb_user_info error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@user_callbacks_router.callback_query(F.data == "users")
async def cb_show_users(call: CallbackQuery):
    """Обработчик для показа списка пользователей."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        users = db.get_all_users()
        if not users:
            await call.message.answer("Нет зарегистрированных пользователей")
            await safe_answer_callback(call)
            return

        await show_users_page_callback(call, users, 1, is_banned=False)

    except Exception as e:
        logger.error(f"cb_show_users error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@user_callbacks_router.callback_query(F.data == "banned")
async def cb_show_banned(call: CallbackQuery):
    """Обработчик для показа заблокированных пользователей."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        banned = db.get_banned_users()
        if not banned:
            await call.message.answer("Нет заблокированных пользователей")
            await safe_answer_callback(call)
            return

        await show_users_page_callback(call, banned, 1, is_banned=True)

    except Exception as e:
        logger.error(f"cb_show_banned error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@user_callbacks_router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main_menu(call: CallbackQuery):
    """Обработчик для возврата в главное меню админа."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        from keyboards import admin_keyboard
        
        try:
            await call.message.edit_text(
                "Добрый день.\nЭто админ панель бота",
                reply_markup=admin_keyboard()
            )
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await call.message.answer(
                "Добрый день.\nЭто админ панель бота",
                reply_markup=admin_keyboard()
            )

        await safe_answer_callback(call)

    except Exception as e:
        logger.error(f"cb_admin_main_menu error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)