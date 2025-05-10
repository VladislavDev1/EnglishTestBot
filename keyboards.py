from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Пользователи", callback_data="users"),
                 InlineKeyboardButton("Заблокированные", callback_data="banned"),)
    return markup