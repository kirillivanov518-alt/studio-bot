from datetime import datetime
import calendar

MONTH_NAMES_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

STUDIO_CLOSE_HOUR = 22  # студия закрывается в 22:00
STUDIO_OPEN_HOUR = 11   # студия открывается в 11:00

def create_calendar(year: int = None, month: int = None):
    """Календарь с зачёркнутыми прошедшими днями"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    markup = InlineKeyboardMarkup(inline_keyboard=[])

    # Заголовок с русским названием месяца
    month_name = MONTH_NAMES_RU[month]
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

            date_obj = datetime(year, month, day)
            date_str = f"{year}-{month:02d}-{day:02d}"

            if date_obj.date() < now.date():
                # Прошедшие дни — зачёркнуты
                row.append(InlineKeyboardButton(text=f"✗{day}", callback_data="ignore"))
            elif date_obj.date() == now.date() and now.hour >= STUDIO_CLOSE_HOUR:
                # Сегодня, но студия уже закрыта
                row.append(InlineKeyboardButton(text=f"✗{day}", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(text=str(day), callback_data=f"date_{date_str}"))
        markup.inline_keyboard.append(row)

    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month % 12 + 1
    next_year = year if month < 12 else year + 1

    nav_row = []
    # Кнопку "назад" показываем только если это не прошлый месяц
    if (year, month) > (now.year, now.month):
        nav_row.append(InlineKeyboardButton(
            text="⬅️ Пред. месяц",
            callback_data=f"prev_{prev_year}_{prev_month}"
        ))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    nav_row.append(InlineKeyboardButton(
        text="След. месяц ➡️",
        callback_data=f"next_{next_year}_{next_month}"
    ))
    markup.inline_keyboard.append(nav_row)

    return markup


def create_time_keyboard(date_str: str):
    """Время 11:00 — 21:00, с учётом текущего времени для сегодня"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    now = datetime.now()
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    is_today = selected_date == now.date()

    markup = InlineKeyboardMarkup(inline_keyboard=[])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text=f"⏰ Время на {date_str}", callback_data="ignore")
    ])

    has_slots = False
    for hour in range(STUDIO_OPEN_HOUR, STUDIO_CLOSE_HOUR):
        # Если сегодня — скрываем прошедшее время
        if is_today and hour <= now.hour:
            continue
        time_str = f"{hour:02d}:00"
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=time_str, callback_data=f"time_{date_str} {time_str}")
        ])
        has_slots = True

    if not has_slots:
        markup.inline_keyboard.append([
            InlineKeyboardButton(text="❌ Нет доступного времени", callback_data="ignore")
        ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к календарю", callback_data="back_to_calendar")
    ])

    return markup


def get_max_duration(hour: int) -> int:
    """Максимальная длительность сессии в зависимости от времени начала"""
    return STUDIO_CLOSE_HOUR - hour  # например 22 - 21 = 1 час


def create_duration_keyboard(date_str: str, time_str: str):
    """Кнопки длительности с учётом максимально допустимого времени"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from tariffs import PRICE_3H, PRICE_5H, PRICE_10H, BASE_PRICE_PER_HOUR

    hour = int(time_str.split(":")[0])
    max_dur = get_max_duration(hour)

    markup = InlineKeyboardMarkup(inline_keyboard=[])

    markup.inline_keyboard.append([
        InlineKeyboardButton(
            text=f"⏱ Максимум {max_dur} ч. (до 22:00)",
            callback_data="ignore"
        )
    ])

    all_packages = [
        (1,  f"1 час — {BASE_PRICE_PER_HOUR} ₽"),
        (3,  f"3 часа — {PRICE_3H} ₽"),
        (5,  f"5 часов — {PRICE_5H} ₽"),
        (10, f"10 часов — {PRICE_10H} ₽"),
    ]

    for dur, label in all_packages:
        if dur <= max_dur:
            markup.inline_keyboard.append([
                InlineKeyboardButton(text=label, callback_data=f"duration_{dur}")
            ])

    # Кастомная длительность — только если есть место
    if max_dur > 1:
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"Другое количество часов (макс. {max_dur})",
                callback_data="duration_custom"
            )
        ])

    markup.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к времени", callback_data="back_to_time")
    ])

    return markup