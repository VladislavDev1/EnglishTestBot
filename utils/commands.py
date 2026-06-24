from typing import List, Tuple

USER_COMMANDS: List[Tuple[str, str]] = [
    ("start", "Перезапустить бота"),
    ("tests", "Запустить тест"),
    ("end", "Завершить тест"),
    ("next", "Следующий тест"),
]

ADMIN_COMMANDS: List[Tuple[str, str]] = [
    ("statistic", "Статистика студентов"),
    ("delete", "Удалить пользователя"),
    ("ban", "Заблокировать пользователя"),
    ("unban", "Разблокировать пользователя"),
]
