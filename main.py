import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import StateFilter



from config import BOT_TOKEN, ADMIN_ID
from logger_config import logger
from utils.commands import USER_COMMANDS, ADMIN_COMMANDS

from keep_alive import keep_alive 

# Import all routers
from handlers import user_router, text_router, poll_router, admin_commands_router
from callbacks import user_callbacks_router, admin_callbacks_router

# Storage
storage = MemoryStorage()

# Create dispatcher and bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

keep_alive()

async def set_commands():
    """Установить команды для пользователей и администратора."""
    user_commands = [BotCommand(command=name, description=desc) for name, desc in USER_COMMANDS]
    await bot.set_my_commands(user_commands)

    admin_commands = [BotCommand(command=name, description=desc) for name, desc in ADMIN_COMMANDS]
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
    logger.info("Commands set successfully")


async def on_startup():
    """Функция, которая выполняется при старте бота."""
    logger.info("Bot starting up...")
    await set_commands()
    logger.info("Bot started successfully")


async def on_shutdown():
    """Функция, которая выполняется при остановке бота."""
    logger.info("Bot shutting down...")
    await bot.session.close()


def setup_handlers():
    """Зарегистрировать все обработчики."""
    # Регистрируем все роутеры
    dp.include_router(admin_commands_router)
    dp.include_router(admin_callbacks_router)
    dp.include_router(user_callbacks_router)
    dp.include_router(user_router)
    dp.include_router(poll_router)
    dp.include_router(text_router)
    
    logger.info("All handlers registered")


async def main():
    """Главная функция."""
    logger.info("="*50)
    logger.info("Bot initialization...")
    logger.info("="*50)
    
    setup_handlers()
    
    try:
        await on_startup()
        logger.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during bot execution: {e}", exc_info=True)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)