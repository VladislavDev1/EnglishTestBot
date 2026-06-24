from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния пользователя."""
    registering = State()  # Ввод данных регистрации (Имя|Фамилия|Группа)
    changing_name = State()  # Изменение имени


class AdminStates(StatesGroup):
    """Состояния администратора."""
    pass