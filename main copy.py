import random
import telebot
from englishDB import Database
from DATA_LISTS_TESTS import tests, TEST2, TEST3, TEST4, TEST5
from config import TOKEN, ADMIN_ID
from time import sleep
from telebot import types

db = Database('english.db')

bot = telebot.TeleBot(token=TOKEN)

# глобальные переменные
correct_count = 0
incorrect_count = 0
correct_answers = {}
message_ids = []
isLoading = False  
count = 0

@bot.message_handler(commands=['tests'])
def starting_test(message):
    if db.user_exist(message.chat.id):
        user_id = message.chat.id
        current_status = db.get_status(user_id)

        if current_status and current_status != 5:
            bot.send_message(user_id, 'У вас есть незавершенный тест. Попробуйте нажать /next')
        else:
            global correct_count, incorrect_count, correct_answers, count
            count = 0
            correct_answers = {}
            correct_count = 0
            incorrect_count = 0

            db.set_status(user_id, 1)
            send_test_questions(user_id, tests)
    else:
        bot.send_message(message.chat.id, 'Вы не зарегистрированы, введите /start')

@bot.message_handler(commands=['next'])
def next_stage(message):
    current_status = db.get_status(message.chat.id)
    if current_status == 1:
        send_test_questions(message.chat.id, TEST2)
        db.set_status(message.chat.id, 2)
    elif current_status == 2:
        send_test_questions(message.chat.id, TEST3)
        db.set_status(message.chat.id, 3)
    elif current_status == 3:
        send_test_questions(message.chat.id, TEST4)
        db.set_status(message.chat.id, 4)
    elif current_status == 4:
        send_test_questions(message.chat.id, TEST5)
        db.set_status(message.chat.id, 5)
    else:
        bot.send_message(message.chat.id, 'Невозможно перейти к следующему этапу')

def send_test_questions(chat_id, test_data):
    random_test = random.sample(list(test_data.keys()), 5)
    markup = types.ReplyKeyboardRemove()

    for i in random_test:
        question_details = test_data[i]
        answer = question_details["answer"]
        options = question_details["options"]

        if answer not in options:
            bot.send_message(chat_id, f"Ошибка в вопросе: {question_details['question']}. Правильный ответ '{answer}' не найден в списке вариантов ответа.")
            continue

        correct_option_index = options.index(answer)

        poll_message = bot.send_poll(
            chat_id,
            question=f'{i} {question_details["question"]}',
            is_anonymous=False,
            options=options,
            type="quiz",
            correct_option_id=correct_option_index,
            reply_markup=markup
        )
        sleep(1)

        question_id = poll_message.poll.id
        correct_answers[question_id] = correct_option_index

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    global correct_count, incorrect_count, message_ids
    user_id = poll_answer.user.id
    selected_option_id = poll_answer.option_ids[0]
    question_id = poll_answer.poll_id
    correct_option_id = correct_answers.get(question_id)

    if selected_option_id == correct_option_id:
        correct_count += 1
    else:
        incorrect_count += 1

    if correct_count + incorrect_count == len(correct_answers):
        db.update_test_info(user_id, correct_count, incorrect_count)
        if db.get_status(user_id) == 5:
            global count
            count += 1
            db.set_test_count(poll_answer.user.id, count)
            bot.send_message(user_id, f'Вы успешно завершили тест, ваши данные отправлены преподавателю!\n\nПравильных ответов: {correct_count}\nНеправильных ответов: {incorrect_count}', reply_markup=None)
            bot.send_message(ADMIN_ID, f"Пользователь: {db.get_user_name(poll_answer.user.id)} только что решил тест\nПравильных ответов: {correct_count}\nНеправильных ответов: {incorrect_count}")
            return
    
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("/next")
        markup.add(btn1)

        message = bot.send_message(user_id, f"{db.get_status(poll_answer.user.id)}/5\nЧтобы продолжить нажмите /next", reply_markup=markup)
        message_ids.append(message.message_id)






@bot.message_handler(commands=['statistic'])
def statistic(message):
    if message.chat.id == ADMIN_ID:
        users = db.get_all_users()
        if users:
            user_list = "\n".join([f"<em><b>{user[1]}: статус {user[2]},</b></em>\nпройдено тестов: {user[3]},\nправильные ответы: {user[4]}\nнеправильные ответы: {user[5]}\n\n" for user in users])
            bot.send_message(ADMIN_ID, f"Зарегистрированные пользователи:\n{user_list}", parse_mode='HTML')
        else:
            bot.send_message(ADMIN_ID, "Нет зарегистрированных пользователей")
    else:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")

@bot.message_handler(commands=['start'])
def welcome(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, 'Добрый день, сюда будет приходить статистика студентов')
    else:
        if db.user_exist(message.chat.id):
            bot.send_message(message.chat.id, f'Добрый день, {message.from_user.first_name}! Вы уже зарегистрированы в системе. Чтобы начать тест, нажмите /tests')
        else:
            bot.send_sticker(message.chat.id, 'CAACAgIAAxkBAAEFVcRmP1fYktDsuSp917lB9SgvmSRBWgACNhYAAnJroEul2k1dhz9kKTUE')
            bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}! Данный бот предназначен для укрепления знаний английского языка.')
            bot.send_message(message.chat.id, 'Чтобы начать тест, пожалуйста, введите своё имя:')
            bot.register_next_step_handler(message, handle_name_input)

def handle_name_input(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(ADMIN_ID, 'Я не отвечаю на текст')
    else:
        user_id = message.chat.id
        name = message.text
        db.add_user(user_id, name)
        bot.send_sticker(message.chat.id, 'CAACAgIAAxkBAAEFVfdmP1uexp-GV72cpq7a-hHHhwUZrwACgxkAAiY7mEhfKtXAStm9azUE')
        bot.send_message(user_id, f'Спасибо, {name}! Теперь вы зарегистрированы в системе. Чтобы начать тест, нажмите /tests')

        chat_id = message.chat.id
        message_id = message.message_id

        for i in range(4):
            bot.delete_message(chat_id, message_id - i)

@bot.message_handler(content_types=['text'])
def text(message):
    if db.user_exist(message.chat.id):
        bot.send_message(message.chat.id, 'Я не отвечаю на текст')
    else:
        bot.send_message(message.chat.id, 'Вы не зарегистрированы, нажмите /start')

# Запуск бота
bot.polling(none_stop=True)
