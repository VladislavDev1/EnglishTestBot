from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import db, safe_answer_callback
from config import ADMIN_ID, USERS_PER_PAGE
from logger_config import logger

admin_callbacks_router = Router()


def create_delete_page_keyboard(page: int, total_pages: int):
    """Создать клавиатуру для страницы удаления."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"delete_page_{page - 1}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"delete_page_{page + 1}"))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)
    
    return kb


async def show_delete_page_callback(call: CallbackQuery, users: list, page: int):
    """Показать страницу удаления пользователей через callback."""
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
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"🗑️ Удалить {u[1]}", callback_data=f"confirm_delete_{u[0]}")
        ])

    nav_kb = create_delete_page_keyboard(page, total_pages)
    kb.inline_keyboard.extend(nav_kb.inline_keyboard)
    
    try:
        await call.message.edit_text("Выберите кого хотите удалить", reply_markup=kb)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await call.message.answer("Выберите кого хотите удалить", reply_markup=kb)
    
    await safe_answer_callback(call)


@admin_callbacks_router.callback_query(F.data.startswith("delete_page_"))
async def cb_delete_page(call: CallbackQuery):
    """Обработчик навигации по страницам удаления."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        page = int(call.data.split("_")[2])
        users = db.get_all_users()
        
        if not users:
            await call.message.answer("Нет пользователей для удаления")
            await safe_answer_callback(call)
            return

        await show_delete_page_callback(call, users, page)

    except Exception as e:
        logger.error(f"cb_delete_page error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@admin_callbacks_router.callback_query(F.data.startswith("confirm_delete_"))
async def cb_confirm_delete(call: CallbackQuery):
    """Обработчик подтверждения удаления."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        user_id = int(call.data.split("_")[2])
        user = db.get_user_by_id(user_id)
        
        if not user:
            await call.message.answer("Пользователь не найден")
            await safe_answer_callback(call)
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"final_delete_yes_{user[0]}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"final_delete_no_{user[0]}"),
            ]
        ])

        try:
            await call.message.edit_text(f"Удалить пользователя {user[1]}?", reply_markup=kb)
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await call.message.answer(f"Удалить пользователя {user[1]}?", reply_markup=kb)

        await safe_answer_callback(call)

    except Exception as e:
        logger.error(f"cb_confirm_delete error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@admin_callbacks_router.callback_query(F.data.startswith("final_delete_"))
async def cb_final_delete(call: CallbackQuery):
    """Обработчик финального удаления."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        parts = call.data.split("_")
        user_id = int(parts[3])
        
        if call.data.startswith("final_delete_yes_"):
            db.delete_user(user_id)
            await safe_answer_callback(call, "✅ Пользователь удалён")
        else:
            await safe_answer_callback(call, "❌ Отменено")

        users = db.get_all_users()
        if users:
            start = 0
            end = USERS_PER_PAGE
            page_users = users[start:end]

            kb = InlineKeyboardMarkup(inline_keyboard=[])
            
            for u in page_users:
                kb.inline_keyboard.append([
                    InlineKeyboardButton(text=f"🗑️ Удалить {u[1]}", callback_data=f"confirm_delete_{u[0]}")
                ])

            nav_kb = create_delete_page_keyboard(1, 1)
            kb.inline_keyboard.extend(nav_kb.inline_keyboard)

            try:
                await call.message.edit_text("Выберите кого хотите удалить", reply_markup=kb)
            except Exception as e:
                logger.warning(f"Failed to edit message: {e}")
                await call.message.answer("Выберите кого хотите удалить", reply_markup=kb)
        else:
            await call.message.answer("Нет пользователей для удаления")

    except Exception as e:
        logger.error(f"cb_final_delete error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@admin_callbacks_router.callback_query(F.data.startswith("delete_user_"))
async def cb_delete_user_ask(call: CallbackQuery):
    """Обработчик запроса удаления пользователя (из профиля)."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        user_id = int(call.data.split("_")[2])
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"delete_yes_{user_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"delete_no_{user_id}"),
            ]
        ])

        try:
            await call.message.edit_text(f"Удалить пользователя {user_id}?", reply_markup=kb)
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await call.message.answer(f"Удалить пользователя {user_id}?", reply_markup=kb)

        await safe_answer_callback(call)

    except Exception as e:
        logger.error(f"cb_delete_user_ask error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@admin_callbacks_router.callback_query(F.data.startswith("delete_yes_") | F.data.startswith("delete_no_"))
async def cb_delete_user_confirm(call: CallbackQuery):
    """Обработчик подтверждения удаления из профиля."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        user_id = int(call.data.split("_")[2])
        
        if call.data.startswith("delete_yes_"):
            username = db.get_user_name(user_id) or str(user_id)
            db.delete_user(user_id)
            db.user_ban(user_id, username, True)
            await safe_answer_callback(call, "✅ Пользователь удалён")
        else:
            await safe_answer_callback(call, "❌ Отменено")

        users = db.get_all_users()
        if users:
            await show_users_list(call, users, 1)
        else:
            await call.message.answer("Нет пользователей")

    except Exception as e:
        logger.error(f"cb_delete_user_confirm error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@admin_callbacks_router.callback_query(F.data.startswith("unban_user_"))
async def cb_unban_ask(call: CallbackQuery):
    """Обработчик запроса разблокировки."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        user_id = int(call.data.split("_")[2])
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"unban_yes_{user_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"unban_no_{user_id}"),
            ]
        ])

        try:
            await call.message.edit_text(f"Разблокировать пользователя {user_id}?", reply_markup=kb)
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            await call.message.answer(f"Разблокировать пользователя {user_id}?", reply_markup=kb)

        await safe_answer_callback(call)

    except Exception as e:
        logger.error(f"cb_unban_ask error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


@admin_callbacks_router.callback_query(F.data.startswith("unban_yes_") | F.data.startswith("unban_no_"))
async def cb_unban_confirm(call: CallbackQuery):
    """Обработчик подтверждения разблокировки."""
    try:
        if call.from_user.id != ADMIN_ID:
            await call.answer("Вам недоступна данная команда", show_alert=True)
            return

        user_id = int(call.data.split("_")[2])
        
        if call.data.startswith("unban_yes_"):
            db.user_unban(user_id)
            await safe_answer_callback(call, "✅ Пользователь разблокирован")
        else:
            await safe_answer_callback(call, "❌ Отменено")

        banned = db.get_banned_users()
        if banned:
            await show_banned_list(call, banned, 1)
        else:
            await call.message.answer("Нет заблокированных пользователей")

    except Exception as e:
        logger.error(f"cb_unban_confirm error: {e}")
        await call.answer("Произошла ошибка", show_alert=True)


async def show_users_list(call: CallbackQuery, users: list, page: int):
    """Показать список пользователей."""
    start = (page - 1) * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for u in page_users:
        kb.inline_keyboard.append([InlineKeyboardButton(text=u[1], callback_data=f"user_{u[0]}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_{page + 1}"))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")])

    try:
        await call.message.edit_text("👥 Зарегистрированные пользователи", reply_markup=kb)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await call.message.answer("👥 Зарегистрированные пользователи", reply_markup=kb)


async def show_banned_list(call: CallbackQuery, users: list, page: int):
    """Показать список заблокированных пользователей."""
    start = (page - 1) * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for u in page_users:
        kb.inline_keyboard.append([InlineKeyboardButton(text=u[1], callback_data=f"user_banned_{u[0]}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_ban_{page - 1}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_ban_{page + 1}"))
    
    if nav_buttons:
        kb.inline_keyboard.append(nav_buttons)
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main_menu")])

    try:
        await call.message.edit_text("🚫 Чёрный список", reply_markup=kb)
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        await call.message.answer("🚫 Чёрный список", reply_markup=kb)