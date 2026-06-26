import random
# import importlib
import time
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import profile_keyboard, next_button_keyboard, remove_keyboard
from utils import check_ban, check_registered, db, notify_admin, UserStates
from utils.feedback import get_final_feedback
from logger_config import logger
from config import TOTAL_STAGES, ADMIN_ID

# module = importlib.import_module("DATA_LISTS_TESTS (transport)")
# tests = module.tests
# TEST2 = module.TEST2
# TEST3 = module.TEST3
# TEST4 = module.TEST4
# TEST5 = module.TEST5

# Импортируем test data
from DATA_LISTS_LAW_STUDENT import TEST1, TEST2, TEST3, TEST4, TEST5

user_router = Router()

# Rate limiter for /next: user_id -> last call timestamp
LAST_NEXT_CALL: dict[int, float] = {}

# Этапы тестов
STAGE_TESTS = {
    1: TEST1,
    2: TEST2,
    3: TEST3,
    4: TEST4,
    5: TEST5,
}


def get_test_data_by_stage(stage: int) -> dict:
    """Получить тестовые данные по номеру этапа."""
    return STAGE_TESTS.get(stage, {})


async def send_stage(message: Message, test_data: dict):
    """
    Отправляет вопросы текущего этапа.
    Сбрасывает счётчики этапа и записывает правильные ответы в БД.
    """
    user_id = message.from_user.id
    db.reset_stage_counters(user_id)

    sample_size = min(5, len(test_data))
    if sample_size == 0:
        logger.error(f"Нет вопросов в test_data для пользователя {user_id}")
        await message.answer("Ошибка: тест не содержит вопросов. Сообщите администратору.")
        return

    selected_keys = random.sample(list(test_data.keys()), sample_size)
    stage_answers: dict[str, int] = {}

    for idx, key in enumerate(selected_keys, 1):
        q = test_data[key]
        answer = q["answer"]
        options = q["options"][:]

        if answer not in options:
            logger.error(f"Вопрос {key}: правильный ответ «{answer}» не в вариантах")
            await message.answer(
                f"Ошибка в вопросе «{q['question']}»: ответ не найден в вариантах. "
                f"Сообщите администратору."
            )
            continue

        random.shuffle(options)
        correct_idx = options.index(answer)

        try:
            poll_msg = await message.answer_poll(
                question=f"{key}. {q['question']}",
                options=options,
                is_anonymous=False,
                type="quiz",
                correct_option_id=correct_idx,
            )
            stage_answers[str(poll_msg.poll.id)] = correct_idx
        except Exception as e:
            logger.error(f"Ошибка при отправке опроса: {e}")

    db.set_stage_answers(user_id, stage_answers)


async def stage_complete_message(message: Message, stage_num: int, correct: int, incorrect: int):
    """
    Вызывается, когда пользователь ответил на все вопросы текущего этапа.
    Прибавляет результаты к суммарным счётчикам.
    Либо предлагает продолжить, либо выводит финальную статистику.
    """
    user_id = message.from_user.id
    db.add_to_total_counts(user_id, correct, incorrect)

    if stage_num < TOTAL_STAGES:
        # Промежуточный этап — предлагаем перейти к следующему
        await message.answer(
            f"✅ Этап {stage_num} из {TOTAL_STAGES} завершён!\n"
            f"Правильных: {correct} | Неправильных: {incorrect}\n\n"
            f"Нажмите /next, чтобы продолжить.",
            reply_markup=next_button_keyboard(),
        )
    else:
        # Финальный этап
        total_correct, total_incorrect = db.get_total_counts(user_id)
        db.increment_test_count(user_id)
        db.set_status(user_id, TOTAL_STAGES)  # финальный статус

        feedback = get_final_feedback(total_correct, total_incorrect)
        print(f"feedback", feedback)
        await message.answer(
            f"🎉 Тест полностью завершён!\n\n"
            f"📊 Итого:\n"
            f"✅ Правильных ответов: {total_correct}\n"
            f"❌ Неправильных ответов: {total_incorrect}\n\n"
            f">{feedback}",
            reply_markup=profile_keyboard(),
            
        )
        
        user_name = db.get_user_name(user_id)
        await notify_admin(
            None,  # будет передан bot в main
            f"👤 {user_name} завершил тест\n"
            f"✅ Правильных: {total_correct}\n"
            f"❌ Неправильных: {total_incorrect}"
        )


@user_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    if db.ban_exist(user_id):
        await message.answer("Вы заблокированы и не можете использовать бота.")
        return

    if user_id == ADMIN_ID:
        from keyboards import admin_keyboard
        await message.answer(
            "Добрый день.\nЭто админ панель бота",
            reply_markup=admin_keyboard()
        )
        return

    if db.user_exist(user_id):
        await message.answer(
            f"Добрый день, {first_name}! "
            "Чтобы начать тест, нажмите /tests",
            reply_markup=profile_keyboard(),
        )
    else:
        try:
            await message.answer_sticker(
                "CAACAgIAAxkBAAERchFqPFTW3dLh49p6cI67ZjaXkOcvmwACTGcAAjDbkEnvgE6VVoXpIDwE"
            )
        except Exception as e:
            logger.warning(f"Failed to send sticker: {e}")

        await message.answer(
            f"Привет, {first_name}! "
            "Данный бот предназначен для укрепления знаний английского языка."
        )
        await message.answer("Введите свои данные в формате Имя|Фамилия|Группа:")
        await state.set_state(UserStates.registering)


@user_router.message(UserStates.registering)
async def register_user(message: Message, state: FSMContext):
    """Обработчик регистрации пользователя."""
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await message.answer("Я не отвечаю на текст")
        return

    name = message.text
    db.add_user(user_id, name)
    await state.clear()

    try:
        await message.answer_sticker(
            "CAACAgIAAxkBAAERcg9qPFPZjbR0lGQkkAez8HZK6omFIgACi14AAkrzYUp2nVqd2p3rtjwE"
        )
    except Exception as e:
        logger.warning(f"Failed to send sticker: {e}")

    await message.answer(
        f"Спасибо, {name}! Вы зарегистрированы. Чтобы начать тест, нажмите /tests",
        reply_markup=profile_keyboard(),
    )

    # Попытаемся удалить сообщения
    try:
        for i in range(4):
            try:
                await message.delete()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Failed to delete messages: {e}")


@user_router.message(Command("tests"))
@check_ban
@check_registered
async def cmd_tests(message: Message):
    """Обработчик команды /tests - начать новый тест."""
    user_id = message.from_user.id
    current_status = db.get_status(user_id)

    # Если тест уже идёт (status между 1 и 4 включительно — этапы не завершены)
    if current_status and current_status != TOTAL_STAGES:
        await message.answer(
            "⚠️ У вас есть незавершённый тест. Попробуйте нажать /next"
        )
        return

    # Начинаем новый тест: статус 1 → этап 1 (tests)
    db.reset_test_info(user_id)
    # Атомарно устанавливаем статус, чтобы избежать гонки при двойном нажатии
    if not db.compare_and_set_status(user_id, current_status, 1):
        await message.answer("⚠️ Действие уже выполняется или было выполнено. Попробуйте снова.")
        return
    await send_stage(message, TEST1)
    
    user_name = db.get_user_name(user_id)
    await notify_admin(None, f"👤 {user_name} начал тестирование")


@user_router.message(Command("next"))
@check_ban
async def cmd_next(message: Message):
    """Обработчик команды /next - переход к следующему этапу."""
    user_id = message.from_user.id
    current_status = db.get_status(user_id)

    # Rate limit: allow /next only once per 5 seconds per user
    now = time.time()
    last = LAST_NEXT_CALL.get(user_id, 0)
    if now - last < 5:
        wait = int(5 - (now - last)) or 1
        await message.answer(f"⚠️ Подождите ещё {wait} сек перед следующим /next.")
        return
    LAST_NEXT_CALL[user_id] = now

    if current_status not in STAGE_TESTS or current_status >= TOTAL_STAGES:
        await message.answer(
            "❌ Невозможно перейти к следующему этапу.\nНачните тест: /tests"
        )
        return

    # Проверяем что текущий этап завершён
    stage_answers = db.get_stage_answers(user_id)
    stage_correct, stage_incorrect = db.get_stage_counts(user_id)
    total_answered = stage_correct + stage_incorrect
    total_questions = len(stage_answers)

    if total_answered < total_questions:
        await message.answer(
            f"⚠️ Сначала ответьте на все вопросы текущего этапа!\n"
            f"Отвечено: {total_answered} из {total_questions}"
        )
        return

    next_status = current_status + 1
    if next_status not in STAGE_TESTS:
        await message.answer(
            "❌ Невозможно перейти к следующему этапу.\nНачните тест: /tests"
        )
        return

    # Пытаемся атомарно обновить статус: если другой запрос уже обновил статус — отменяем
    if not db.compare_and_set_status(user_id, current_status, next_status):
        await message.answer("⚠️ Другой запрос уже обработан — попробуйте ещё раз.")
        return

    next_test = STAGE_TESTS[next_status]
    await send_stage(message, next_test)


@user_router.message(Command("end"))
@check_ban
@check_registered
async def cmd_end(message: Message):
    """Сбросить все прогрессы теста и подготовиться к новому запуску."""
    user_id = message.from_user.id
    current_status = db.get_status(user_id)

    if not current_status or current_status == 0:
        await message.answer("У вас нет активного теста.")
        return

    # Сбрасываем прогресс и статус
    db.reset_test_info(user_id)
    db.set_status(user_id, 0)

    await message.answer(
        "✅ Тест сброшен. Вы можете начать новый тест: /tests",
        reply_markup=profile_keyboard(),
    )