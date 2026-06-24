from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def profile_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой профиля."""
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="👤 Профиль")]],
        resize_keyboard=True
    )
    return kb


def next_button_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для перехода к следующему этапу."""
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/next")]],
        resize_keyboard=True
    )
    return kb


def profile_edit_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура профиля с опциями редактирования."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="Изменить имя")],
        ],
        resize_keyboard=True
    )
    return kb


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаление клавиатуры."""
    return ReplyKeyboardRemove()