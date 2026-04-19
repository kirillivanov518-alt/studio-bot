from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tariffs import get_duration_text

def get_duration_keyboard():
    """Кнопки выбора длительности"""
    # Импорт внутри функции — решает circular import
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    special_packages = [1, 3, 5, 10]
    
    for dur in special_packages:
        if dur == 3:
            text = "3 часа — 2990 ₽"
        elif dur == 5:
            text = "5 часов — 4999 ₽"
        elif dur == 10:
            text = "10 часов — 9799 ₽"
        else:
            text = get_duration_text(dur)
        
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=text, callback_data=f"duration_{dur}")
        ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="Другое количество часов", callback_data="duration_custom")
    ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="← Назад к времени", callback_data="back_to_time")
    ])

    return markup