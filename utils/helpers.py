from functools import wraps
from aiogram import Bot
from englishDB import Database
from config import ADMIN_ID
from logger_config import logger

db = Database("english2.db")


def check_admin(func):
    """Декоратор для проверки, является ли пользователь админом."""
    @wraps(func)
    async def wrapper(message_or_call, *args, **kwargs):
        user_id = message_or_call.from_user.id if hasattr(message_or_call, 'from_user') else message_or_call.message.chat.id
        
        if user_id != ADMIN_ID:
            if hasattr(message_or_call, 'answer'):  # callback query
                await message_or_call.answer("Вам недоступна данная команда", show_alert=True)
            else:
                await message_or_call.answer("Вам недоступна данная команда")
            return
        
        return await func(message_or_call, *args, **kwargs)
    
    return wrapper


def check_ban(func):
    """Декоратор для проверки статуса блокировки."""
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if db.ban_exist(user_id):
            await message.answer("Вы заблокированы и не можете использовать бота.")
            return
        
        return await func(message, *args, **kwargs)
    
    return wrapper


def check_registered(func):
    """Декоратор для проверки регистрации."""
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if not db.user_exist(user_id):
            await message.answer("Вы не зарегистрированы, введите /start")
            return
        
        return await func(message, *args, **kwargs)
    
    return wrapper


async def notify_admin(bot: Bot, text: str):
    """Безопасная отправка уведомления администратору."""
    try:
        await bot.send_message(ADMIN_ID, text)
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")


async def safe_answer_callback(call, text: str = ""):
    """Безопасный ответ на callback query."""
    try:
        await call.answer(text=text)
    except Exception as e:
        logger.warning(f"Failed to answer callback: {e}")


async def safe_edit_message(chat_id: int, message_id: int, text: str, reply_markup=None, bot: Bot = None):
    """Безопасное редактирование сообщения."""
    if not bot:
        return
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as send_error:
            logger.error(f"Failed to send message: {send_error}")