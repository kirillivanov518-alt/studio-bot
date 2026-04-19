from datetime import datetime
import calendar

def create_calendar(year: int = None, month: int = None):
    """Календарь без кнопки предыдущего месяца"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    markup = InlineKeyboardMarkup(inline_keyboard=[])

    # Заголовок
    month_name = calendar.month_name[month]
    markup.inline_keyboard.append([
        InlineKeyboardButton(text=f"📅 {month_name} {year}", callback_data="ignore")
    ])

    # Дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.inline_keyboard.append([
        InlineKeyboardButton(text=day, callback_data="ignore") for day in days
    ])

    # Дни месяца
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            date_str = f"{year}-{month:02d}-{day:02d}"
            date_obj = datetime(year, month, day)

            if date_obj.date() < now.date():
                row.append(InlineKeyboardButton(text=f"🪦{day}", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(text=str(day), callback_data=f"date_{date_str}"))
        markup.inline_keyboard.append(row)

    # Только следующий месяц
    next_month = month % 12 + 1
    next_year = year if month < 12 else year + 1
    markup.inline_keyboard.append([
        InlineKeyboardButton(text="➡️ Следующий месяц", callback_data=f"next_{next_year}_{next_month}")
    ])

    return markup


def create_time_keyboard(date_str: str):
    """Время 11:00 — 21:00"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    
    markup.inline_keyboard.append([
        InlineKeyboardButton(text=f"⏰ Время на {date_str}", callback_data="ignore")
    ])

    for hour in range(11, 22):
        time_str = f"{hour:02d}:00"
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=time_str, callback_data=f"time_{date_str} {time_str}")
        ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="← Назад к календарю", callback_data="back_to_calendar")
    ])

    return markup