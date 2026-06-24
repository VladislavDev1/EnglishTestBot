from functools import wraps
from config import ADMIN_IDS


def admin_only(handler):
    def wrapper(update, context, *args, **kwargs):
        user_id = getattr(update, "effective_user", None)
        if user_id and user_id.id in ADMIN_IDS:
            return handler(update, context, *args, **kwargs)
        return "Доступ запрещён"

    return wraps(handler)(wrapper)
