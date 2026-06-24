import os
import random
import logging
import telebot
from englishDB import Database
from DATA_LISTS_TESTS import TEST2, TEST3, TEST4, TEST5, tests
from time import sleep
from telebot import types
from keyboards import admin_keyboard
# from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# keep_alive()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not ADMIN_ID_RAW or not ADMIN_ID_RAW.lstrip("-").isdigit():
    raise RuntimeError("ADMIN_ID не задан или некорректен в .env")

ADMIN_ID = int(ADMIN_ID_RAW)

db = Database("english2.db")
bot = telebot.TeleBot(token=TOKEN)
bot.remove_webhook()

# Этапы: status → (тест, следующий_status)
# status=1 → TEST2 (уже отправлен при /tests), после него status=2
# status=2 → TEST3, после него status=3
# ...
# status=5 → финал, тест завершён
STAGE_TESTS = {
    1: tests,
    2: TEST2,
    3: TEST3,
    4: TEST4,
    5: TEST5,
}
TOTAL_STAGES = 5  # финальный статус



# ===========================================================================
# Утилиты
# ===========================================================================

def check_ban_status(user_id: int) -> bool:
    """Возвращает True и отправляет сообщение, если пользователь заблокирован."""
    if db.ban_exist(user_id):
        bot.send_message(user_id, "Вы заблокированы и не можете использовать бота.")
        return True
    return False


def notify_admin(text: str):
    """Безопасная отправка уведомления администратору."""
    try:
        bot.send_message(ADMIN_ID, text)
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")


def send_stage(chat_id: int, test_data: dict):
    """
    Отправляет вопросы текущего этапа.
    Сбрасывает счётчики этапа и записывает правильные ответы в БД.
    """
    db.reset_stage_counters(chat_id)

    sample_size = min(5, len(test_data))
    if sample_size == 0:
        logger.error(f"Нет вопросов в test_data для пользователя {chat_id}")
        bot.send_message(chat_id, "Ошибка: тест не содержит вопросов. Сообщите администратору.")
        return

    selected_keys = random.sample(list(test_data.keys()), sample_size)
    stage_answers: dict[str, int] = {}
    markup_remove = types.ReplyKeyboardRemove()

    for key in selected_keys:
        q = test_data[key]
        answer = q["answer"]
        options = q["options"][:]

        if answer not in options:
            logger.error(f"Вопрос {key}: правильный ответ «{answer}» не в вариантах")
            bot.send_message(
                chat_id,
                f"Ошибка в вопросе «{q['question']}»: ответ не найден в вариантах. "
                f"Сообщите администратору.",
            )
            continue

        random.shuffle(options)
        correct_idx = options.index(answer)

        try:
            msg = bot.send_poll(
                chat_id,
                question=f"{key}. {q['question']}",
                is_anonymous=False,
                options=options,
                type="quiz",
                correct_option_id=correct_idx,
                reply_markup=markup_remove,
            )
            stage_answers[msg.poll.id] = correct_idx
        except telebot.apihelper.ApiTelegramException as e:
            logger.warning(f"Не удалось отправить poll пользователю {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке poll: {e}")

    db.set_stage_answers(chat_id, stage_answers)


def _stage_complete_message(chat_id: int, stage_num: int, correct: int, incorrect: int):
    """
    Вызывается, когда пользователь ответил на все вопросы текущего этапа.
    Прибавляет результаты к суммарным счётчикам.
    Либо предлагает продолжить, либо выводит финальную статистику.
    """
    db.add_to_total_counts(chat_id, correct, incorrect)

    if stage_num < TOTAL_STAGES:
        # Промежуточный этап — предлагаем перейти к следующему
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("/next"))
        bot.send_message(
            chat_id,
            f"Этап {stage_num} из {TOTAL_STAGES} завершён!\n"
            f"Правильных: {correct} | Неправильных: {incorrect}\n\n"
            f"Нажмите /next, чтобы продолжить.",
            reply_markup=markup,
        )
    else:
        # Финальный этап
        # Финальный этап (stage_num = 4, TEST5 уже пройден)
        total_correct, total_incorrect = db.get_total_counts(chat_id)
        db.increment_test_count(chat_id)
        db.set_status(chat_id, TOTAL_STAGES)  # финальный статус

        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("👤 Профиль"))

        bot.send_message(
            chat_id,
            f"🎉 Тест полностью завершён!\n\n"
            f"📊 Итого:\n"
            f"✅ Правильных ответов: {total_correct}\n"
            f"❌ Неправильных ответов: {total_incorrect}",
            reply_markup=markup,
        )
        notify_admin(
            f"👤 {db.get_user_name(chat_id)} завершил тест\n"
            f"✅ Правильных: {total_correct}\n"
            f"❌ Неправильных: {total_incorrect}"
        )


# ===========================================================================
# Команды
# ===========================================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = message.chat.id

    if check_ban_status(user_id):
        return

    if user_id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "Добрый день.\nЭто админ панель бота", reply_markup=admin_keyboard())
        return

    markup_profile = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_profile.add(types.KeyboardButton("👤 Профиль"))

    if db.user_exist(user_id):
        bot.send_message(
            user_id,
            f"Добрый день, {message.from_user.first_name}! Вы уже зарегистрированы. "
            f"Чтобы начать тест, нажмите /tests",
            reply_markup=markup_profile,
        )
    else:
        bot.send_sticker(
            user_id,
            "CAACAgIAAxkBAAEFVcRmP1fYktDsuSp917lB9SgvmSRBWgACNhYAAnJroEul2k1dhz9kKTUE",
        )
        bot.send_message(
            user_id,
            f"Привет, {message.from_user.first_name}! "
            f"Данный бот предназначен для укрепления знаний английского языка.",
        )
        bot.send_message(user_id, "Введите свои данные в формате Имя|Фамилия|Группа:")
        bot.register_next_step_handler(message, _register_user)


def _register_user(message):
    user_id = message.chat.id

    if user_id == ADMIN_ID:
        bot.send_message(ADMIN_ID, "Я не отвечаю на текст")
        return

    name = message.text
    db.add_user(user_id, name)

    markup_profile = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_profile.add(types.KeyboardButton("👤 Профиль"))

    bot.send_sticker(
        user_id,
        "CAACAgIAAxkBAAEFVfdmP1uexp-GV72cpq7a-hHHhwUZrwACgxkAAiY7mEhfKtXAStm9azUE",
    )
    bot.send_message(
        user_id,
        f"Спасибо, {name}! Вы зарегистрированы. Чтобы начать тест, нажмите /tests",
        reply_markup=markup_profile,
    )

    # Пробуем удалить последние несколько сообщений (приветствие + ввод)
    for i in range(4):
        try:
            bot.delete_message(user_id, message.message_id - i)
        except Exception:
            pass


@bot.message_handler(commands=["tests"])
def cmd_tests(message):
    user_id = message.chat.id

    if check_ban_status(user_id):
        return

    if not db.user_exist(user_id):
        bot.send_message(user_id, "Вы не зарегистрированы, введите /start")
        return

    current_status = db.get_status(user_id)

    # Если тест уже идёт (status между 1 и 4 включительно — этапы не завершены)
    if current_status and current_status != TOTAL_STAGES:
        bot.send_message(user_id, "У вас есть незавершённый тест. Попробуйте нажать /next")
        return

    # Начинаем новый тест: статус 1 → этап 1 (TEST2)
    db.reset_test_info(user_id)
    db.set_status(user_id, 1)
    send_stage(user_id, tests)
    notify_admin(f"👤 {db.get_user_name(user_id)} начал тестирование")


@bot.message_handler(commands=["next"])
def cmd_next(message):
    user_id = message.chat.id

    if check_ban_status(user_id):
        return

    current_status = db.get_status(user_id)

    if current_status not in STAGE_TESTS:
        bot.send_message(user_id, "Невозможно перейти к следующему этапу.\nНачните тест: /tests")
        return

    # Проверяем что текущий этап завершён
    stage_answers = db.get_stage_answers(user_id)
    stage_correct, stage_incorrect = db.get_stage_counts(user_id)
    total_answered = stage_correct + stage_incorrect
    total_questions = len(stage_answers)

    if total_answered < total_questions:
        bot.send_message(user_id, f"⚠️ Сначала ответьте на все вопросы текущего этапа!\n"
                                  f"Отвечено: {total_answered} из {total_questions}")
        return

    next_test = STAGE_TESTS[current_status]
    next_status = current_status + 1
    db.set_status(user_id, next_status)
    send_stage(user_id, next_test)
    
# ===========================================================================
# Обработка ответов на опросы
# ===========================================================================

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    selected_idx = poll_answer.option_ids[0]

    stage_answers = db.get_stage_answers(user_id)

    logger.info(f"[poll] user={user_id}, poll_id={poll_id!r} (type={type(poll_id).__name__})")
    logger.info(f"[poll] stage_answers keys={list(stage_answers.keys())[:3]} (type={type(next(iter(stage_answers), None)).__name__})")


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
    _stage_complete_message(user_id, current_status, stage_correct, stage_incorrect)


# ===========================================================================
# Текстовые сообщения
# ===========================================================================

@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.chat.id

    if check_ban_status(user_id):
        return

    text = message.text

    if text == "👤 Профиль":
        _show_profile(message)
    elif text == "🔙Назад":
        cmd_start(message)
    elif text == "Изменить имя":
        bot.send_message(user_id, "Введите новое имя:")
        bot.register_next_step_handler(message, _handle_change_name)
    elif db.user_exist(user_id):
        bot.send_message(user_id, "Я не отвечаю на текст")
    else:
        bot.send_message(user_id, "Вы не зарегистрированы, нажмите /start")


def _show_profile(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙Назад"), types.KeyboardButton("Изменить имя"))
    bot.send_message(
        user_id,
        f"Ваш профиль:\n\n🆔 ID: {user_id}\n👤 Имя: {db.get_user_name(user_id)}",
        reply_markup=markup,
    )


def _handle_change_name(message):
    user_id = message.chat.id
    markup_profile = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_profile.add(types.KeyboardButton("👤 Профиль"))

    if message.text in ("👤 Профиль", "Изменить имя", "🔙Назад"):
        bot.send_message(user_id, "Пожалуйста, введите корректное имя!")
        return

    db.update_user_name(user_id, message.text)
    bot.send_message(
        user_id,
        f"Имя успешно изменено на «{message.text}».",
        reply_markup=markup_profile,
    )


# ===========================================================================
# Админ: статистика / пагинация пользователей
# ===========================================================================

@bot.message_handler(commands=["statistic"])
def cmd_statistic(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")
        return
    users = db.get_all_users()
    if users:
        _show_users_page(message.chat.id, users, 1)
    else:
        bot.send_message(ADMIN_ID, "Нет зарегистрированных пользователей")


def _show_users_page(chat_id, users, page, message_id=None, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]

    keyboard = types.InlineKeyboardMarkup()
    for u in page_users:
        keyboard.add(types.InlineKeyboardButton(u[1], callback_data=f"user_{u[0]}"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page - 1}"))
    if end < len(users):
        nav.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"page_{page + 1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="admin_main_menu"))

    text = "Зарегистрированные пользователи"
    _send_or_edit(chat_id, message_id, text, keyboard)


def _show_banned_page(chat_id, users, page, message_id=None, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]

    keyboard = types.InlineKeyboardMarkup()
    for u in page_users:
        keyboard.add(types.InlineKeyboardButton(u[1], callback_data=f"user_banned_{u[0]}"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_ban_{page - 1}"))
    if end < len(users):
        nav.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"page_ban_{page + 1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="admin_main_menu"))

    _send_or_edit(chat_id, message_id, "Чёрный список", keyboard)


def _send_or_edit(chat_id, message_id, text, keyboard):
    """Редактирует существующее сообщение или отправляет новое."""
    if message_id:
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
            )
            return
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                return
            logger.warning(f"edit_message_text failed: {e}")
    bot.send_message(chat_id, text, reply_markup=keyboard)


def _safe_answer(call_id, text=""):
    try:
        bot.answer_callback_query(call_id, text=text)
    except Exception:
        pass


# ===========================================================================
# Callback: навигация по пользователям / страницам
# ===========================================================================

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("page_") or c.data.startswith("user_")
)
def cb_user_navigation(call):
    try:
        data = call.data
        mid = call.message.message_id
        cid = call.message.chat.id

        if data.startswith("page_ban_"):
            page = int(data.split("_")[2])
            _show_banned_page(cid, db.get_banned_users(), page, mid)

        elif data.startswith("page_"):
            page = int(data.split("_")[1])
            _show_users_page(cid, db.get_all_users(), page, mid)

        elif data.startswith("user_banned_"):
            user_id = int(data.split("_")[2])
            user = db.get_banned_user_by_id(user_id)
            if not user:
                bot.send_message(cid, "Пользователь не найден")
                return
            _safe_answer(call.id, user[1])
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Разблокировать", callback_data=f"unban_user_{user[0]}"))
            kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="page_ban_1"))
            bot.edit_message_text(
                chat_id=cid,
                message_id=mid,
                text=f"ID: {user[0]}\nИмя: {user[1]}",
                reply_markup=kb,
            )

        elif data.startswith("user_"):
            user_id = int(data.split("_")[1])
            user = db.get_user_by_id(user_id)
            if not user:
                bot.send_message(cid, "Пользователь не найден")
                return
            _safe_answer(call.id, user[1])
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Удалить и заблокировать", callback_data=f"delete_user_{user[0]}"))
            kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="page_1"))
            info = (
                f"Имя: {user[1]}\n"
                f"ID: {user[0]}\n"
                f"Статус: {user[2]}\n"
                f"Пройдено тестов: {user[3]}\n"
                f"Правильных: {user[4]}\n"
                f"Неправильных: {user[5]}"
            )
            bot.edit_message_text(chat_id=cid, message_id=mid, text=info, reply_markup=kb)

    except Exception as e:
        logger.error(f"cb_user_navigation error: {e}")


# ===========================================================================
# Callback: удаление пользователя
# ===========================================================================

@bot.callback_query_handler(func=lambda c: c.data.startswith("delete_user_"))
def cb_delete_user_ask(call):
    try:
        user_id = int(call.data.split("_")[2])
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("Да", callback_data=f"delete_yes_{user_id}"),
            types.InlineKeyboardButton("Нет", callback_data=f"delete_no_{user_id}"),
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Удалить пользователя {user_id}?",
            reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"cb_delete_user_ask error: {e}")


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("delete_yes_") or c.data.startswith("delete_no_")
)
def cb_delete_user_confirm(call):
    try:
        user_id = int(call.data.split("_")[2])
        if call.data.startswith("delete_yes_"):
            username = db.get_user_name(user_id) or str(user_id)
            db.delete_user(user_id)
            db.user_ban(user_id, username, True)
            _safe_answer(call.id, "Пользователь удалён")
        else:
            _safe_answer(call.id, "Отменено")
        _show_users_page(call.message.chat.id, db.get_all_users(), 1, call.message.message_id)
    except Exception as e:
        logger.error(f"cb_delete_user_confirm error: {e}")


# ===========================================================================
# Callback: разблокировка
# ===========================================================================

@bot.callback_query_handler(func=lambda c: c.data.startswith("unban_user_"))
def cb_unban_ask(call):
    try:
        user_id = int(call.data.split("_")[2])
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("Да", callback_data=f"unban_yes_{user_id}"),
            types.InlineKeyboardButton("Нет", callback_data=f"unban_no_{user_id}"),
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Разблокировать пользователя {user_id}?",
            reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"cb_unban_ask error: {e}")


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("unban_yes_") or c.data.startswith("unban_no_")
)
def cb_unban_confirm(call):
    try:
        user_id = int(call.data.split("_")[2])
        if call.data.startswith("unban_yes_"):
            db.user_unban(user_id)
            _safe_answer(call.id, "Пользователь разблокирован")
        else:
            _safe_answer(call.id, "Отменено")
        _show_users_page(call.message.chat.id, db.get_all_users(), 1, call.message.message_id)
    except Exception as e:
        logger.error(f"cb_unban_confirm error: {e}")


# ===========================================================================
# Callback: показ заблокированных / всех пользователей / главное меню
# ===========================================================================

@bot.callback_query_handler(func=lambda c: c.data == "banned")
def cb_show_banned(call):
    try:
        _safe_answer(call.id, "Заблокированные пользователи")
        banned = db.get_banned_users()
        if banned:
            _show_banned_page(call.message.chat.id, banned, 1, call.message.message_id)
        else:
            bot.send_message(ADMIN_ID, "Нет заблокированных пользователей")
    except Exception as e:
        logger.error(f"cb_show_banned error: {e}")


@bot.callback_query_handler(func=lambda c: c.data == "users")
def cb_show_users(call):
    try:
        _safe_answer(call.id, "Пользователи")
        users = db.get_all_users()
        if users:
            _show_users_page(call.message.chat.id, users, 1, call.message.message_id)
        else:
            bot.send_message(ADMIN_ID, "Нет зарегистрированных пользователей")
    except Exception as e:
        logger.error(f"cb_show_users error: {e}")


@bot.callback_query_handler(func=lambda c: c.data == "admin_main_menu")
def cb_admin_main_menu(call):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Добрый день.\nЭто админ панель бота",
            reply_markup=admin_keyboard(),
        )
        _safe_answer(call.id)
    except Exception as e:
        logger.error(f"cb_admin_main_menu error: {e}")


# ===========================================================================
# Админ: /ban /unban /delete
# ===========================================================================

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        bot.reply_to(message, "Укажите корректный ID: /ban <user_id>")
        return

    user_id = int(parts[1])
    if db.ban_exist(user_id):
        bot.send_message(ADMIN_ID, "Пользователь уже заблокирован")
        return

    username = db.get_user_name(user_id) or "Неизвестный пользователь"
    db.user_ban(user_id, username, True)
    bot.send_message(ADMIN_ID, f"Пользователь {username} заблокирован!")


@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        bot.reply_to(message, "Укажите корректный ID: /unban <user_id>")
        return

    user_id = int(parts[1])
    if not db.ban_exist(user_id):
        bot.send_message(ADMIN_ID, "Пользователь не был заблокирован")
        return

    db.user_unban(user_id)
    username = db.get_user_name(user_id) or str(user_id)
    bot.send_message(ADMIN_ID, f"Пользователь {username} разблокирован!")


@bot.message_handler(commands=["delete"])
def cmd_delete(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")
        return
    users = db.get_all_users()
    if users:
        _show_delete_page(message.chat.id, users, 1)
    else:
        bot.send_message(ADMIN_ID, "Нет зарегистрированных пользователей")


def _show_delete_page(chat_id, users, page, message_id=None, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]

    kb = types.InlineKeyboardMarkup()
    for u in page_users:
        kb.add(types.InlineKeyboardButton(f"Удалить {u[1]}", callback_data=f"confirm_delete_{u[0]}"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"delete_page_{page - 1}"))
    if end < len(users):
        nav.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"delete_page_{page + 1}"))
    if nav:
        kb.add(*nav)

    _send_or_edit(chat_id, message_id, "Выберите кого хотите удалить", kb)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("confirm_delete_") or c.data.startswith("delete_page_")
)
def cb_delete_page(call):
    try:
        data = call.data
        cid = call.message.chat.id
        mid = call.message.message_id

        if data.startswith("delete_page_"):
            page = int(data.split("_")[2])
            _show_delete_page(cid, db.get_all_users(), page, mid)

        elif data.startswith("confirm_delete_"):
            user_id = int(data.split("_")[2])
            user = db.get_user_by_id(user_id)
            if user:
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("Да", callback_data=f"final_delete_yes_{user[0]}"),
                    types.InlineKeyboardButton("Нет", callback_data=f"final_delete_no_{user[0]}"),
                )
                bot.edit_message_text(
                    chat_id=cid,
                    message_id=mid,
                    text=f"Удалить пользователя {user[1]}?",
                    reply_markup=kb,
                )
    except Exception as e:
        logger.error(f"cb_delete_page error: {e}")


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("final_delete_yes_") or c.data.startswith("final_delete_no_")
)
def cb_final_delete(call):
    try:
        user_id = int(call.data.split("_")[3])
        if call.data.startswith("final_delete_yes_"):
            db.delete_user(user_id)
            _safe_answer(call.id, "Пользователь удалён")
        else:
            _safe_answer(call.id, "Отменено")
        _show_delete_page(call.message.chat.id, db.get_all_users(), 1, call.message.message_id)
    except Exception as e:
        logger.error(f"cb_final_delete error: {e}")


# ===========================================================================
# Запуск
# ===========================================================================

if __name__ == "__main__":
    logger.info("Бот запущен")
    while True:
        try:
            bot.polling(
                none_stop=True,
                allowed_updates=["message", "callback_query", "poll_answer"]
            )
        except telebot.apihelper.ApiTelegramException as e:
            if e.result.status_code == 502:
                logger.warning("Bad Gateway, повтор через 15 сек...")
                sleep(15)
            else:
                logger.exception("Telegram API exception")
                sleep(15)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}. Повтор через 15 сек...")
            sleep(15)