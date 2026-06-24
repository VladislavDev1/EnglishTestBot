from handlers.user_handlers import user_router
from handlers.text_handlers import text_router
from handlers.poll_handlers import poll_router
from handlers.admin_handlers import admin_commands_router

__all__ = [
    "user_router",
    "text_router",
    "poll_router",
    "admin_commands_router",
]