from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    """Главное меню бота"""
    keyboard = [
        [KeyboardButton(text="📅 Записаться в студию")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)