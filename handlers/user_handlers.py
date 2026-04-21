from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import re

from keyboards.main_menu import get_main_menu
from keyboards.booking import get_sound_engineer_keyboard, get_confirm_keyboard
from states import BookingStates
from utils.calendar import create_calendar, create_time_keyboard, create_duration_keyboard
from tariffs import calculate_cost, calculate_prepayment, get_duration_text
from database import save_booking, get_user_bookings, get_booking_by_id, cancel_booking, is_slot_taken
from config import ADMIN_ID

router = Router()


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^(\+7|7|8)\d{10}$', cleaned))


def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))


def can_refund(booking_date: str, booking_time: str) -> bool:
    session_dt = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
    return session_dt - datetime.now() > timedelta(hours=24)


# ====================== Главное меню ======================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="👋 Привет! Добро пожаловать в студию звукозаписи!\n\nВыбери действие в меню ниже 👇",
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
             "📋 <b>Мои записи</b> — просмотр и отмена броней\n\n"
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
    buttons = []

    for b in bookings:
        status_icon = "✅" if b["status"] == "confirmed" else "❌"
        text += (
            f"{status_icon} <b>#{b['id']}</b> — {b['date']} в {b['time']}\n"
            f"⏱ {get_duration_text(b['duration'])} | 🎤 {'Да' if b['sound_engineer'] else 'Нет'}\n"
            f"💰 {b['amount']} ₽ (пред. {b['prepayment']} ₽)\n"
            f"──────────────\n"
        )
        if b["status"] == "confirmed":
            buttons.append([InlineKeyboardButton(
                text=f"❌ Отменить бронь #{b['id']}",
                callback_data=f"cancel_booking_{b['id']}"
            )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


# ====================== Отмена брони ======================
@router.callback_query(F.data.startswith("cancel_booking_"))
async def ask_cancel_booking(callback: CallbackQuery):
    booking_id = int(callback.data.replace("cancel_booking_", ""))
    booking = await get_booking_by_id(booking_id)

    if not booking or booking["status"] != "confirmed":
        await callback.answer("❌ Бронь не найдена или уже отменена.", show_alert=True)
        return

    refund = can_refund(booking["date"], booking["time"])
    refund_text = (
        "✅ Предоплата будет возвращена (до сессии больше 24 часов)"
        if refund else
        "⚠️ Предоплата НЕ возвращается (до сессии меньше 24 часов)"
    )

    await callback.message.answer(
        text=f"Ты хочешь отменить бронь <b>#{booking_id}</b>?\n\n"
             f"📅 {booking['date']} в {booking['time']}\n"
             f"⏱ {get_duration_text(booking['duration'])}\n\n"
             f"{refund_text}\n\nПодтвердить отмену?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"confirm_cancel_{booking_id}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_bookings")
            ]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel_"))
async def confirm_cancel_booking(callback: CallbackQuery, bot):
    booking_id = int(callback.data.replace("confirm_cancel_", ""))
    booking = await get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("❌ Бронь не найдена.", show_alert=True)
        return

    await cancel_booking(booking_id)
    refund = can_refund(booking["date"], booking["time"])

    await callback.message.edit_text(
        text=f"✅ Бронь <b>#{booking_id}</b> отменена.\n\n"
             + ("💸 Предоплата будет возвращена в течение 3-5 дней."
                if refund else
                "⚠️ Предоплата не возвращается — отмена менее чем за 24 часа."),
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"❌ <b>Отмена брони #{booking_id}</b>\n\n"
                 f"👤 {booking['client_name']}\n"
                 f"📱 {booking['phone']}\n"
                 f"📅 {booking['date']} в {booking['time']}\n"
                 f"⏱ {get_duration_text(booking['duration'])}\n\n"
                 + (f"💸 Нужно вернуть предоплату: {booking['prepayment']} ₽"
                    if refund else
                    "💰 Предоплата не возвращается"),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer()


@router.callback_query(F.data == "back_to_bookings")
async def back_to_bookings(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


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

    if await is_slot_taken(date_str, time_str):
        await callback.answer("❌ Это время уже занято, выбери другое!", show_alert=True)
        return

    await state.update_data(selected_date=date_str, selected_time=time_str)
    await callback.message.edit_text(
        text=f"✅ Выбрано:\n📅 Дата: <b>{date_str}</b>\n⏰ Время: <b>{time_str}</b>\n\n⏱ Выбери длительность сессии:",
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
            f"✏️ Введи количество часов от 1 до {max_dur}:\n(только целые числа)"
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
        duration = int(message.text.strip())
    except ValueError:
        await message.answer(f"❌ Введи целое число (например: 2)\nМаксимум: {max_dur} ч.")
        return

    if duration < 1 or duration > max_dur:
        await message.answer(
            f"❌ Введи число от 1 до {max_dur}:",
            parse_mode="HTML"
        )
        return

    await _set_duration(message, state, float(duration), edit=False)


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
            "❌ Номер не распознан. Попробуй ещё раз.\n\nПримеры:\n<b>+79001234567</b>\n<b>89001234567</b>",
            parse_mode="HTML"
        )
        return
    await state.update_data(phone=phone)
    await message.answer("📧 Введите email для чека:\n\nПример: <b>example@mail.ru</b>", parse_mode="HTML")
    await state.set_state(BookingStates.waiting_for_email)


# ====================== Email ======================
@router.message(BookingStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer("❌ Email не распознан.\n\nПример: <b>example@mail.ru</b>", parse_mode="HTML")
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
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot):
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

    engineer_text = "Да" if data.get("sound_engineer") else "Нет"

    await callback.message.edit_text(
        text=f"✅ <b>Бронирование подтверждено!</b>\n\n"
             f"📅 {data['selected_date']} в {data['selected_time']}\n"
             f"⏱ {get_duration_text(data['duration'])}\n"
             f"🎤 Звукорежиссёр: {engineer_text}\n"
             f"💸 Предоплата: <b>{data['prepayment']} ₽</b>\n\n"
             f"🔖 Номер брони: <b>#{booking_id}</b>\n\n"
             "Посмотреть и отменить бронь — кнопка 📋 Мои записи",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>Новая бронь #{booking_id}!</b>\n\n"
                 f"👤 {data['client_name']}\n"
                 f"📱 {data['phone']}\n"
                 f"📧 {data['email']}\n"
                 f"📅 {data['selected_date']} в {data['selected_time']}\n"
                 f"⏱ {get_duration_text(data['duration'])}\n"
                 f"🎤 Звукарь: {engineer_text}\n"
                 f"💬 {data.get('comment') or 'нет'}\n\n"
                 f"💰 {data['full_cost']} ₽ | Предоплата: {data['prepayment']} ₽",
            parse_mode="HTML"
        )
    except Exception:
        pass

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
        text=f"✅ Выбрано:\n📅 Дата: <b>{date_str}</b>\n⏰ Время: <b>{time_str}</b>\n\n⏱ Выбери длительность:",
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


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu())