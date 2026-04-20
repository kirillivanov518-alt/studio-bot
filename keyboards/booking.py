from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_sound_engineer_keyboard():
    """Кнопки Да/Нет для звукорежиссёра"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="engineer_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="engineer_no"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к длительности", callback_data="back_to_duration")
        ]
    ])


def get_confirm_keyboard():
    """Кнопки подтверждения бронирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_engineer")
        ]
    ])


def get_contact_keyboard():
    """Кнопка назад на этапе сбора контактов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_engineer")
        ]
    ])