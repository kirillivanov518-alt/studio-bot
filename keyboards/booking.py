from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_duration_keyboard():
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    for dur in [1, 2, 3, 4, 5, 6]:
        if dur == 3:
            text = "3 часа — 2990 ₽"
        else:
            text = f"{dur} час{'а' if dur == 1 else 'ов'}"
        markup.inline_keyboard.append([InlineKeyboardButton(text=text, callback_data=f"duration_{dur}")])

    markup.inline_keyboard.append([InlineKeyboardButton(text="Другое количество часов", callback_data="duration_custom")])
    markup.inline_keyboard.append([InlineKeyboardButton(text="← Назад к времени", callback_data="back_to_time")])

    return markup