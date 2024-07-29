import random
import telebot
from englishDB import Database
from DATA_LISTS_TESTS import tests, TEST2, TEST3, TEST4, TEST5
from config import TOKEN, ADMIN_ID
from time import sleep
from telebot import types
from telebot import apihelper





# connect DB + create bot
db = Database('english.db')
bot = telebot.TeleBot(token=TOKEN) 


# проверка бана
def check_ban_status(user_id):
    if db.ban_exist(user_id):
        bot.send_message(user_id, "Вы заблокированы и не можете использовать бота.")
        return True
    return False

# tests commend for start testing open
@bot.message_handler(commands=['tests'])
def starting_test(message):
    user_id = message.chat.id

    # проверка бана
    if check_ban_status(user_id):
        return
    if db.user_exist(user_id):
        current_status = db.get_status(user_id)
        if current_status and current_status != 5:
            bot.send_message(user_id, 'У вас есть незавершенный тест. Попробуйте нажать /next')
        else:
            db.set_status(user_id, 1)  # Устанавливаем начальный статус для пользователя
            db.reset_test_info(user_id)  # Сбрасываем информацию о тесте для пользователя
            send_test_questions(user_id, tests)  # Отправляем вопросы первого этапа
    else:
        bot.send_message(user_id, 'Вы не зарегистрированы, введите /start')
# tests commend for start testing close



# next commant for skip current text open 
@bot.message_handler(commands=['next'])
def next_stage(message):
    user_id = message.chat.id
    
# проверка бана
    if check_ban_status(user_id):
        return
    current_status = db.get_status(user_id)
    if current_status == 1:
        send_test_questions(user_id, TEST2)
        db.set_status(user_id, 2)
    elif current_status == 2:
        send_test_questions(user_id, TEST3)
        db.set_status(user_id, 3)
    elif current_status == 3:
        send_test_questions(user_id, TEST4)
        db.set_status(user_id, 4)
    elif current_status == 4:
        send_test_questions(user_id, TEST5)
        db.set_status(user_id, 5)
    else:
        bot.send_message(user_id, 'Невозможно перейти к следующему этапу')

def send_test_questions(chat_id, test_data):
    random_test = random.sample(list(test_data.keys()), 5)
    markup = types.ReplyKeyboardRemove()
    correct_answers = db.get_correct_answers(chat_id)  # Получаем существующие правильные ответы

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

        question_id = poll_message.poll.id
        correct_answers[question_id] = correct_option_index  # Добавляем новый правильный ответ


    db.set_correct_answers(chat_id, correct_answers)  # Сохраняем обновленные правильные ответы в базу данных

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    user_id = poll_answer.user.id
    selected_option_id = poll_answer.option_ids[0]
    question_id = poll_answer.poll_id
    correct_answers = db.get_correct_answers(user_id)  # Получаем правильные ответы из базы данных
    correct_option_id = correct_answers.get(question_id)

# проверка бана
    if check_ban_status(user_id):
        return
    
    if correct_option_id is None:
        return

    if selected_option_id == correct_option_id:
        db.increment_correct_count(user_id)  # Увеличиваем счетчик правильных ответов
    else:
        db.increment_incorrect_count(user_id)  # Увеличиваем счетчик неправильных ответов

    correct_count = db.get_correct_count(user_id)
    incorrect_count = db.get_incorrect_count(user_id)
    total_questions = len(correct_answers)

    
    if correct_count + incorrect_count == total_questions:
        db.update_test_info(user_id, correct_count, incorrect_count)  # Обновляем информацию о тесте в базе данных 
        if db.get_status(user_id) == 5:
            markupProfile = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn = types.KeyboardButton("👤 Профиль")
            btn1 = types.KeyboardButton("Изменить имя")
            markupProfile.add(btn, btn1)

            db.increment_test_count(user_id)  # Увеличиваем счетчик завершенных тестов
            bot.send_message(user_id, f'Вы успешно завершили тест, ваши данные отправлены преподавателю!\n\nПравильных ответов: {correct_count}\nНеправильных ответов: {incorrect_count}', reply_markup=markupProfile)
            bot.send_message(ADMIN_ID, f"Пользователь: {db.get_user_name(user_id)} только что решил тест\nПравильных ответов: {correct_count}\nНеправильных ответов: {incorrect_count}")

        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("/next")
            markup.add(btn1)
            bot.send_message(user_id, f"{db.get_status(user_id)}/5\nЧтобы продолжить нажмите /next", reply_markup=markup)
# next commant for skip current text close




# ADMIN----------------------------------------------------------------------------------------------------------------ADMIN

# statistic user open
@bot.message_handler(commands=['statistic'])
def statistic(message):
    if message.chat.id == ADMIN_ID:
        users = db.get_all_users()
        if users:
            show_users_page(message.chat.id, users, 1)
        else:
            bot.send_message(ADMIN_ID, "Нет зарегистрированных пользователей")
    else:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")

def show_users_page(chat_id, users, page, message_id=None, users_per_page=10):
    start_index = (page - 1) * users_per_page
    end_index = start_index + users_per_page
    users_page = users[start_index:end_index]
    
    # user_list = "\n".join([f"<em><b>{user[1]}: статус {user[2]},</b></em>\nпройдено тестов: {user[3]},\nправильные ответы: {user[4]}\nнеправильные ответы: {user[5]}\n\n" for user in users_page])
    
    keyboard = types.InlineKeyboardMarkup()
    
    for user in users_page:
        user_button = types.InlineKeyboardButton(
            text=f"{user[1]}",
            callback_data=f"user_{user[0]}"
        )
        keyboard.add(user_button)
    
    # Add navigation buttons
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
    if end_index < len(users):
        navigation_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
    
    if navigation_buttons:
        keyboard.add(*navigation_buttons)
    
    if message_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='Зарегестрированные пользователи', parse_mode='HTML', reply_markup=keyboard)
    else:
        bot.send_message(chat_id, 'Зарегестрированные пользователи', parse_mode='HTML', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_') or call.data.startswith('user_'))
def callback_user_navigation(call):
    if call.data.startswith('page_'):
        page = int(call.data.split('_')[1])
        users = db.get_all_users()
        show_users_page(call.message.chat.id, users, page, message_id=call.message.message_id)
    elif call.data.startswith('user_'):
        user_id = int(call.data.split('_')[1])
        user = db.get_user_by_id(user_id)
        if user:
            user_info = (f"Имя: {user[1]}\n"
                         f"ID: {user[0]}\n"
                         f"Статус: {user[2]}\n"
                         f"Пройдено тестов: {user[3]}\n"
                         f"Правильные ответы: {user[4]}\n"
                         f"Неправильные ответы: {user[5]}")
            bot.send_message(call.message.chat.id, user_info)
        else:
            bot.send_message(call.message.chat.id, "Пользователь не найден")
# statistic user close


# ban user open

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.chat.id == ADMIN_ID:
        
        command_parts = message.text.split()

        if len(command_parts) < 2:
            bot.reply_to(message, "Ошибка: Не указан ID пользователя. Используйте команду /ban <user_id>")
            return

        user_id = command_parts[1]

        if db.ban_exist(user_id):
            bot.send_message(ADMIN_ID, 'Пользователь уже был заблокирован')
        else:
            db.user_ban(user_id, True)
            user_name = db.get_user_name(user_id)
            bot.send_message(ADMIN_ID, f'Пользователь {user_name} заблокирован!')
    else:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")
        
        
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.chat.id == ADMIN_ID:
        command_parts = message.text.split()

        if len(command_parts) < 2:
            bot.reply_to(message, "Ошибка: Не указан ID пользователя. Используйте команду /unban <user_id>")
            return

        user_id = command_parts[1]

        if not db.ban_exist(user_id):
            bot.send_message(ADMIN_ID, 'Пользователь не был заблокирован')
        else:
            db.user_ban(user_id, False)
            user_name = db.get_user_name(user_id)
            bot.send_message(ADMIN_ID, f'Пользователь {user_name} разблокирован!')

    else:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")
        
    
# ban user close


#--------------------------


# delete user functions open
@bot.message_handler(commands=['delete'])
def delete_user(message):
    if message.chat.id == ADMIN_ID:
        users = db.get_all_users()
        if users:
            show_delete_users_page(message.chat.id, users, 1)
        else:
            bot.send_message(ADMIN_ID, "Нет зарегистрированных пользователей")
    else:
        bot.send_message(message.chat.id, "Вам недоступна данная команда")

def show_delete_users_page(chat_id, users, page, message_id=None, users_per_page=10):
    start_index = (page - 1) * users_per_page
    end_index = start_index + users_per_page
    users_page = users[start_index:end_index]
    
    # user_list = "\n".join([f"<em><b>{user[1]}: статус {user[2]},</b></em>\nпройдено тестов: {user[3]},\nправильные ответы: {user[4]}\nнеправильные ответы: {user[5]}\n\n" for user in users_page])
    
    keyboard = types.InlineKeyboardMarkup()
    
    for user in users_page:
        delete_button = types.InlineKeyboardButton(
            text=f"Удалить {user[1]}",
            callback_data=f"confirm_delete_{user[0]}"
        )
        keyboard.add(delete_button)
    
    # Add navigation buttons
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"delete_page_{page-1}"))
    if end_index < len(users):
        navigation_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"delete_page_{page+1}"))
    
    if navigation_buttons:
        keyboard.add(*navigation_buttons)
    
    if message_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='Выбирете кого хотите удалить', parse_mode='HTML', reply_markup=keyboard)
    else:
        bot.send_message(chat_id, 'Выбирете кого хотите удалить', parse_mode='HTML', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_') or call.data.startswith('delete_page_') or call.data.startswith('delete_user_'))
def callback_delete_user(call):
    if call.data.startswith('delete_page_'):
        page = int(call.data.split('_')[2])
        users = db.get_all_users()
        show_delete_users_page(call.message.chat.id, users, page, message_id=call.message.message_id)
    elif call.data.startswith('confirm_delete_'):
        user_id = int(call.data.split('_')[2])
        user = db.get_user_by_id(user_id)
        if user:
            confirm_delete_user(call.message.chat.id, user, call.message.message_id)
    elif call.data.startswith('delete_user_'):
        action, user_id = call.data.split('_')[2], int(call.data.split('_')[3])
        if action == 'yes':
            db.delete_user(user_id)
            bot.answer_callback_query(call.id, text="Пользователь удален")
        elif action == 'no':
            bot.answer_callback_query(call.id, text="Удаление отменено")
        users = db.get_all_users()
        show_delete_users_page(call.message.chat.id, users, 1, message_id=call.message.message_id)

def confirm_delete_user(chat_id, user, message_id):
    keyboard = types.InlineKeyboardMarkup()
    yes_button = types.InlineKeyboardButton("Да", callback_data=f"delete_user_yes_{user[0]}")
    no_button = types.InlineKeyboardButton("Нет", callback_data=f"delete_user_no_{user[0]}")
    keyboard.add(yes_button, no_button)
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"Вы уверены, что хотите удалить пользователя {user[1]}?",
        reply_markup=keyboard
    )

# delete user functions close


# start + register user function open
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.chat.id
    markupProfile = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("👤 Профиль")
    btn1 = types.KeyboardButton("Изменить имя")
    markupProfile.add(btn, btn1)
# проверка бана
    if check_ban_status(user_id):
        return
    
    if user_id == ADMIN_ID:
        bot.send_message(ADMIN_ID, 'Добрый день, сюда будет приходить статистика студентов')
    else:
        
        if db.user_exist(user_id):
            
            bot.send_message(user_id, f'Добрый день, {message.from_user.first_name}! Вы уже зарегистрированы в системе. Чтобы начать тест, нажмите /tests', reply_markup=markupProfile)
        else:
            bot.send_sticker(user_id, 'CAACAgIAAxkBAAEFVcRmP1fYktDsuSp917lB9SgvmSRBWgACNhYAAnJroEul2k1dhz9kKTUE')
            bot.send_message(user_id, f'Привет, {message.from_user.first_name}! Данный бот предназначен для укрепления знаний английского языка.')
            bot.send_message(user_id, 'Чтобы начать тест, пожалуйста, введите своё имя:')
            bot.register_next_step_handler(message, handle_name_input)


def handle_name_input(message):
    user_id = message.chat.id
    markupProfile = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("👤 Профиль")
    btn1 = types.KeyboardButton("Изменить имя")
    markupProfile.add(btn, btn1)
    
    if user_id == ADMIN_ID:
        bot.send_message(ADMIN_ID, 'Я не отвечаю на текст')
    else:
        name = message.text
        db.add_user(user_id, name)  # Добавляем пользователя в базу данных
        bot.send_sticker(user_id, 'CAACAgIAAxkBAAEFVfdmP1uexp-GV72cpq7a-hHHhwUZrwACgxkAAiY7mEhfKtXAStm9azUE')
        bot.send_message(user_id, f'Спасибо, {name}! Теперь вы зарегистрированы в системе. Чтобы начать тест, нажмите /tests', reply_markup=markupProfile)
        chat_id = message.chat.id
        message_id = message.message_id
        for i in range(4):
            bot.delete_message(chat_id, message_id - i)
# start + register user function close



# text handler open
@bot.message_handler(content_types=['text'])
def text(message):
# проверка бана
    if check_ban_status(message.chat.id):
        return
    
    
    if (message.text == '👤 Профиль'):
        bot.send_message(message.chat.id, f'Ваш профиль:\n\n🆔 ID: {message.chat.id}\n👤 Имя: {db.get_user_name(message.chat.id)}')
    elif (message.text == 'Изменить имя'):
        bot.send_message(message.chat.id, 'Введите новое имя:')
        bot.register_next_step_handler(message, handle_change_name)
    elif(db.user_exist(message.chat.id)):
         bot.send_message(message.chat.id, 'Я не отвечаю на текст')
    else:
        bot.send_message(message.chat.id, 'Вы не зарегистрированы, нажмите /start')

def handle_change_name(message):
    if message.text == '👤 Профиль' or message.text ==  "Изменить имя":
        bot.send_message(message.chat.id, 'Пожалуйста введите корректное имя!!')
    else:
        user_id = message.chat.id
        new_name = message.text
        db.update_user_name(user_id, new_name)  # Обновляем имя пользователя в базе данных
        bot.send_message(user_id, f'Ваше имя было успешно изменено на {new_name}.')

# text handler close



# Запуск бота
try:
    bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
except Exception as e:
    print(f"Error occurred: {e}")
    sleep(15)