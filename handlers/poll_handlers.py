from aiogram import Router, Bot, F
from aiogram.types import PollAnswer, Message
from englishDB import Database
from logger_config import logger
from config import TOTAL_STAGES

from handlers.user_handlers import stage_complete_message

poll_router = Router()
db = Database("english2.db")


@poll_router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer, bot: Bot):
    """Обработчик ответов на опросы."""
    user_id = poll_answer.user.id
    poll_id = str(poll_answer.poll_id)
    selected_idx = poll_answer.option_ids[0]

    stage_answers = db.get_stage_answers(user_id)

    logger.info(f"[poll] user={user_id}, poll_id={poll_id}")
    logger.info(f"[poll] stage_answers keys={list(stage_answers.keys())[:3]}")

    if poll_id not in stage_answers:
        logger.warning(
            f"poll_id {poll_id} не найден в stage_answers пользователя {user_id}. "
            f"Возможно, ответ пришёл после перехода к следующему этапу."
        )
        return

    correct_idx = stage_answers[poll_id]
    if selected_idx == correct_idx:
        db.increment_stage_correct(user_id)
    else:
        db.increment_stage_incorrect(user_id)

    stage_correct, stage_incorrect = db.get_stage_counts(user_id)
    total_answered = stage_correct + stage_incorrect
    total_questions = len(stage_answers)

    if total_answered < total_questions:
        # Этап ещё не завершён
        return

    # Этап завершён
    current_status = db.get_status(user_id)
    db.add_to_total_counts(user_id, stage_correct, stage_incorrect)
    
    # Отправляем сообщение с результатом этапа
    # Нам нужно получить chat_id для отправки сообщения
    try:
        # Получаем информацию о последнем сообщении пользователя через его ID
        # В aiogram нам нужно отправить сообщение чтобы выполнить stage_complete_message
        # Создаём временное Message-подобное объект или отправляем через bot
        await bot.send_message(
            user_id,
            f"✅ Этап {current_status} из {TOTAL_STAGES} завершён!\n"
            f"Правильных: {stage_correct} | Неправильных: {stage_incorrect}\n\n"
            f"Нажмите /next, чтобы продолжить.",
        )
    except Exception as e:
        logger.error(f"Failed to send stage complete message: {e}")

    # Обновляем статус / показываем следующий этап или финал
    if current_status < TOTAL_STAGES:
        from keyboards import next_button_keyboard
        await bot.send_message(
            user_id,
            f"Перейдите к следующему этапу!",
            reply_markup=next_button_keyboard()
        )
    else:
        # Финальный этап
        total_correct, total_incorrect = db.get_total_counts(user_id)
        db.increment_test_count(user_id)
        db.set_status(user_id, TOTAL_STAGES)

        from keyboards import profile_keyboard
        from utils.feedback import get_final_feedback

        feedback = get_final_feedback(total_correct, total_incorrect)
        await bot.send_message(
            user_id,
            f"🎉 Тест полностью завершён!\n\n"
            f"📊 Итого:\n"
            f"✅ Правильных ответов: {total_correct}\n"
            f"❌ Неправильных ответов: {total_incorrect}\n\n"
            f"> {feedback}",
            reply_markup=profile_keyboard(),
        )

        user_name = db.get_user_name(user_id)
        try:
            from config import ADMIN_ID
            await bot.send_message(
                ADMIN_ID,
                f"👤 {user_name} завершил тест\n"
                f"✅ Правильных: {total_correct}\n"
                f"❌ Неправильных: {total_incorrect}"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")