from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import re

from keyboards.main_menu import get_main_menu
from keyboards.booking import get_sound_engineer_keyboard, get_confirm_keyboard
from states import BookingStates
from utils.calendar import create_calendar, create_time_keyboard, create_duration_keyboard
from tariffs import calculate_cost, calculate_prepayment, get_duration_text
from database import save_booking, get_user_bookings

router = Router()


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^(\+7|7|8)\d{10}$', cleaned))


def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))


# ====================== Главное меню ======================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="👋 Привет! Добро пожаловать в студию звукозаписи skör!\n\n"
             "Выбери действие в меню ниже 👇",
        reply_markup=get_main_menu()
    )


# ====================== Помощь ======================
@router.message(F.text == "❓ Помощь")
async def help_handler(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/sfysamee")]
    ])
    await message.answer(
        text="ℹ️ <b>Как пользоваться ботом:</b>\n\n"
             "📅 <b>Записаться в студию</b> — выбери дату, время и длительность\n"
             "📋 <b>Мои записи</b> — просмотр твоих броней\n\n"
             "<b>Тарифы:</b>\n"
             "• 1 час — 1110 ₽\n"
             "• 3 часа — 2990 ₽\n"
             "• 5 часов — 4999 ₽\n"
             "• 10 часов — 9799 ₽\n"
             "• Звукорежиссёр — +400 ₽/час\n\n"
             "<b>Режим работы:</b> 11:00 — 22:00\n\n"
             "<b>Отмена брони:</b> возврат предоплаты только за 24+ часа до сессии\n\n"
             "Если возникли вопросы — напиши нам 👇",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ====================== Мои записи ======================
@router.message(F.text == "📋 Мои записи")
async def my_bookings(message: Message):
    bookings = await get_user_bookings(message.from_user.id)
    if not bookings:
        await message.answer("У тебя пока нет броней.\n\nНажми 📅 Записаться в студию!", reply_markup=get_main_menu())
        return

    text = "📋 <b>Твои записи:</b>\n\n"
    for b in bookings:
        text += (
            f"🗓 <b>{b['date']}</b> в <b>{b['time']}</b>\n"
            f"⏱ {get_duration_text(b['duration'])}\n"
            f"🎤 Звукорежиссёр: {'Да' if b['sound_engineer'] else 'Нет'}\n"
            f"💰 Сумма: {b['amount']} ₽ (предоплата: {b['prepayment']} ₽)\n"
            f"📌 Статус: {b['status']}\n"
            f"──────────────\n"
        )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu())


# ====================== Начало бронирования ======================
@router.message(F.text == "📅 Записаться в студию")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text="📆 Выбери дату записи:", reply_markup=create_calendar())
    await state.set_state(BookingStates.waiting_for_date)


# ====================== Навигация по месяцам ======================
@router.callback_query(F.data.startswith("next_"))
async def next_month(callback: CallbackQuery):
    parts = callback.data.split("_")
    year, month = int(parts[1]), int(parts[2])
    await callback.message.edit_text(text="📆 Выбери дату записи:", reply_markup=create_calendar(year, month))
    await callback.answer()


@router.callback_query(F.data.startswith("prev_"))
async def prev_month(callback: CallbackQuery):
    parts = callback.data.split("_")
    year, month = int(parts[1]), int(parts[2])
    await callback.message.edit_text(text="📆 Выбери дату записи:", reply_markup=create_calendar(year, month))
    await callback.answer()


# ====================== Выбор даты ======================
@router.callback_query(F.data.startswith("date_"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data[5:]
    await state.update_data(selected_date=date_str)
    await callback.message.edit_text(
        text=f"✅ Дата: <b>{date_str}</b>\n\n⏰ Выбери время начала:",
        reply_markup=create_time_keyboard(date_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_time)
    await callback.answer()


# ====================== Выбор времени ======================
@router.callback_query(F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    full_dt = callback.data[5:]
    date_str, time_str = full_dt.split(" ")
    await state.update_data(selected_date=date_str, selected_time=time_str)
    await callback.message.edit_text(
        text=f"✅ Выбрано:\n"
             f"📅 Дата: <b>{date_str}</b>\n"
             f"⏰ Время: <b>{time_str}</b>\n\n"
             "⏱ Выбери длительность сессии:",
        reply_markup=create_duration_keyboard(date_str, time_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_duration)
    await callback.answer()


# ====================== Выбор длительности (кнопки) ======================
@router.callback_query(F.data.startswith("duration_"))
async def process_duration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    time_str = data.get("selected_time", "11:00")
    hour = int(time_str.split(":")[0])
    max_dur = 22 - hour

    if callback.data == "duration_custom":
        await callback.message.edit_text(
            f"✏️ Введи количество часов от 1 до {max_dur}:\n"
            f"(можно дробное, например: 1.5 или 2)"
        )
        await state.set_state(BookingStates.waiting_for_custom_duration)
        await callback.answer()
        return

    duration = float(callback.data[9:])
    if duration > max_dur:
        await callback.answer(f"❌ Максимум {max_dur} ч. при старте в {time_str}", show_alert=True)
        return

    await _set_duration(callback.message, state, duration, edit=True)
    await callback.answer()


# ====================== Выбор длительности (своё число) ======================
@router.message(BookingStates.waiting_for_custom_duration)
async def process_custom_duration(message: Message, state: FSMContext):
    data = await state.get_data()
    time_str = data.get("selected_time", "11:00")
    hour = int(time_str.split(":")[0])
    max_dur = 22 - hour

    try:
        duration = float(message.text.strip().replace(",", "."))
    except ValueError:
        await message.answer(f"❌ Введи число (например: 2 или 1.5)\nМаксимум: {max_dur} ч.")
        return

    if duration < 1:
        await message.answer(f"❌ Минимум 1 час. Введи число от 1 до {max_dur}:")
        return

    if duration > max_dur:
        await message.answer(
            f"❌ При старте в {time_str} максимум <b>{max_dur} ч.</b> (студия до 22:00)\n"
            f"Введи число от 1 до {max_dur}:",
            parse_mode="HTML"
        )
        return

    await _set_duration(message, state, duration, edit=False)


async def _set_duration(msg, state: FSMContext, duration: float, edit: bool):
    await state.update_data(duration=duration)
    data = await state.get_data()
    full_cost = calculate_cost(duration, False)

    text = (
        f"✅ Выбрано:\n"
        f"📅 Дата: <b>{data['selected_date']}</b>\n"
        f"⏰ Время: <b>{data['selected_time']}</b>\n"
        f"⏱ Длительность: <b>{get_duration_text(duration)}</b>\n"
        f"💰 Стоимость: <b>{full_cost} ₽</b>\n\n"
        f"🎤 Нужен ли звукорежиссёр?\n(+400 ₽/час)"
    )

    if edit:
        await msg.edit_text(text=text, reply_markup=get_sound_engineer_keyboard(), parse_mode="HTML")
    else:
        await msg.answer(text=text, reply_markup=get_sound_engineer_keyboard(), parse_mode="HTML")

    await state.set_state(BookingStates.waiting_for_sound_engineer)


# ====================== Звукорежиссёр ======================
@router.callback_query(F.data.in_(["engineer_yes", "engineer_no"]))
async def process_engineer(callback: CallbackQuery, state: FSMContext):
    needs_engineer = callback.data == "engineer_yes"
    data = await state.get_data()
    duration = data["duration"]
    full_cost = calculate_cost(duration, needs_engineer)
    prepayment = calculate_prepayment(full_cost)
    await state.update_data(sound_engineer=needs_engineer, full_cost=full_cost, prepayment=prepayment)

    await callback.message.edit_text(text="👤 Введите ваше имя:")
    await state.set_state(BookingStates.waiting_for_name)
    await callback.answer()


# ====================== Имя ======================
@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Имя слишком короткое. Введите ваше имя:")
        return
    await state.update_data(client_name=name)
    await message.answer(
        "📱 Введите номер телефона:\n\nФормат: <b>+79001234567</b> или <b>89001234567</b>",
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_phone)


# ====================== Телефон ======================
@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not is_valid_phone(phone):
        await message.answer(
            "❌ Номер не распознан. Попробуй ещё раз.\n\n"
            "Примеры правильного формата:\n"
            "<b>+79001234567</b>\n"
            "<b>89001234567</b>",
            parse_mode="HTML"
        )
        return
    await state.update_data(phone=phone)
    await message.answer(
        "📧 Введите email для чека:\n\nПример: <b>example@mail.ru</b>",
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_email)


# ====================== Email ======================
@router.message(BookingStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer(
            "❌ Email не распознан. Попробуй ещё раз.\n\n"
            "Пример: <b>example@mail.ru</b>",
            parse_mode="HTML"
        )
        return
    await state.update_data(email=email)
    await message.answer(
        "💬 Есть комментарий к брони?\n\nНапиши или отправь <b>—</b> если нет",
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_comment)


# ====================== Комментарий ======================
@router.message(BookingStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    if comment in ["—", "-", "нет", "Нет"]:
        comment = ""
    await state.update_data(comment=comment)

    data = await state.get_data()
    engineer_text = "Да" if data.get("sound_engineer") else "Нет"

    await message.answer(
        text=f"📋 <b>Проверь данные брони:</b>\n\n"
             f"👤 Имя: <b>{data['client_name']}</b>\n"
             f"📱 Телефон: <b>{data['phone']}</b>\n"
             f"📧 Email: <b>{data['email']}</b>\n"
             f"📅 Дата: <b>{data['selected_date']}</b>\n"
             f"⏰ Время: <b>{data['selected_time']}</b>\n"
             f"⏱ Длительность: <b>{get_duration_text(data['duration'])}</b>\n"
             f"🎤 Звукорежиссёр: <b>{engineer_text}</b>\n"
             f"💬 Комментарий: <b>{data['comment'] or 'нет'}</b>\n\n"
             f"💰 Полная стоимость: <b>{data['full_cost']} ₽</b>\n"
             f"💸 Предоплата (10%): <b>{data['prepayment']} ₽</b>\n\n"
             "Всё верно?",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard()
    )
    await state.set_state(BookingStates.waiting_for_payment)


# ====================== Подтверждение ======================
@router.callback_query(F.data == "confirm_yes", BookingStates.waiting_for_payment)
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    booking_id = await save_booking(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username or "",
        date=data["selected_date"],
        time=data["selected_time"],
        duration=data["duration"],
        sound_engineer=data.get("sound_engineer", False),
        phone=data["phone"],
        email=data["email"],
        client_name=data["client_name"],
        comment=data.get("comment", ""),
        amount=data["full_cost"],
        prepayment=data["prepayment"]
    )

    await callback.message.edit_text(
        text=f"✅ <b>Бронирование подтверждено!</b>\n\n"
             f"📅 {data['selected_date']} в {data['selected_time']}\n"
             f"⏱ {get_duration_text(data['duration'])}\n"
             f"🎤 Звукорежиссёр: {'Да' if data.get('sound_engineer') else 'Нет'}\n"
             f"💸 Предоплата: <b>{data['prepayment']} ₽</b>\n\n"
             f"🔖 Номер брони: <b>#{booking_id}</b>\n\n"
             "Оплата через ЮKassa будет добавлена в ближайшее время.\n"
             "Для отмены брони используй /cancel",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "confirm_no")
async def cancel_confirm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Бронирование отменено.")
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()


# ====================== Кнопки НАЗАД ======================
@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📆 Выбери дату записи:", reply_markup=create_calendar())
    await state.set_state(BookingStates.waiting_for_date)
    await callback.answer()


@router.callback_query(F.data == "back_to_time")
async def back_to_time(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_str = data.get("selected_date", "")
    await callback.message.edit_text(
        text=f"✅ Дата: <b>{date_str}</b>\n\n⏰ Выбери время начала:",
        reply_markup=create_time_keyboard(date_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_time)
    await callback.answer()


@router.callback_query(F.data == "back_to_duration")
async def back_to_duration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_str = data.get("selected_date", "")
    time_str = data.get("selected_time", "")
    await callback.message.edit_text(
        text=f"✅ Выбрано:\n"
             f"📅 Дата: <b>{date_str}</b>\n"
             f"⏰ Время: <b>{time_str}</b>\n\n"
             "⏱ Выбери длительность сессии:",
        reply_markup=create_duration_keyboard(date_str, time_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_duration)
    await callback.answer()


@router.callback_query(F.data == "back_to_engineer")
async def back_to_engineer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    duration = data.get("duration", 1)
    full_cost = calculate_cost(duration, False)
    await callback.message.edit_text(
        text=f"⏱ Длительность: <b>{get_duration_text(duration)}</b>\n"
             f"💰 Стоимость: <b>{full_cost} ₽</b>\n\n"
             f"🎤 Нужен ли звукорежиссёр?\n(+400 ₽/час)",
        reply_markup=get_sound_engineer_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_sound_engineer)
    await callback.answer()


# ====================== Игнор пустых кнопок ======================
@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


# ====================== Отмена ======================
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu())