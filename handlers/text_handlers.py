from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import profile_keyboard, profile_edit_keyboard
from utils import check_ban, db, UserStates
from logger_config import logger

text_router = Router()


@text_router.message(F.text == "👤 Профиль")
@check_ban
async def show_profile(message: Message):
    """Показать профиль пользователя."""
    user_id = message.from_user.id

    user_info = db.get_user_by_id(user_id)
    if not user_info:
        await message.answer("Ошибка: пользователь не найден")
        return

    name = user_info[1]  # name
    test_count = user_info[3]  # test_count
    correct_answers = user_info[4]  # correct_answers
    incorrect_answers = user_info[5]  # incorrect_answers

    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Имя: {name}\n"
        f"📝 Пройдено тестов: {test_count}\n"
        f"✅ Всего правильных: {correct_answers}\n"
        f"❌ Всего неправильных: {incorrect_answers}"
    )

    await message.answer(profile_text, reply_markup=profile_edit_keyboard())


@text_router.message(F.text == "🔙 Назад")
@check_ban
async def go_back(message: Message):
    """Вернуться назад."""
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=profile_keyboard(),
    )


@text_router.message(F.text == "Изменить имя")
@check_ban
async def ask_change_name(message: Message, state: FSMContext):
    """Запросить новое имя."""
    await message.answer("Введите новое имя:")
    await state.set_state(UserStates.changing_name)


@text_router.message(UserStates.changing_name)
@check_ban
async def handle_change_name(message: Message, state: FSMContext):
    """Обработать изменение имени."""
    user_id = message.from_user.id
    new_name = message.text

    # Проверяем, что это не кнопка клавиатуры
    if new_name in ("👤 Профиль", "Изменить имя", "🔙 Назад"):
        await message.answer("Пожалуйста, введите корректное имя!")
        return

    db.update_user_name(user_id, new_name)
    await state.clear()

    await message.answer(
        f"✅ Имя успешно изменено на «{new_name}».",
        reply_markup=profile_keyboard(),
    )


@text_router.message(F.text)
@check_ban
async def default_text_handler(message: Message):
    """Обработчик по умолчанию для текстовых сообщений."""
    user_id = message.from_user.id

    if db.user_exist(user_id):
        await message.answer("🤔 Я не отвечаю на текст. Используйте команды или кнопки.")
    else:
        await message.answer("Вы не зарегистрированы, нажмите /start")