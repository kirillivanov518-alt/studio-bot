from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.main_menu import get_main_menu
from keyboards.booking import get_duration_keyboard
from states import BookingStates
from utils.calendar import create_calendar, create_time_keyboard
from tariffs import calculate_cost, calculate_prepayment

router = Router()

# Временный отладочный хендлер (можно удалить позже)
@router.message()
async def debug_fallback(message: Message):
    if message.text and "Записаться в студию" in message.text:
        await start_booking(message, None)  # вызовем основной хендлер

# ====================== Старт ======================
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        text="👋 Привет! Добро пожаловать в студию звукозаписи!\n\n"
             "Выбери действие в меню ниже 👇",
        reply_markup=get_main_menu()
    )

# ====================== Начало брони ======================
# Запуск бронирования
@router.message(F.text.contains("Записаться в студию"))
async def start_booking(message: Message, state: FSMContext):
    await message.answer(
        text="📆 Выбери дату записи:",
        reply_markup=create_calendar()
    )
    await state.set_state(BookingStates.waiting_for_date)

# ====================== Выбор даты ======================
@router.callback_query(F.data.startswith("date_"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    await state.update_data(selected_date=date_str)
    
    await callback.message.edit_text(
        text=f"✅ Дата: <b>{date_str}</b>\n\n⏰ Выбери время начала:",
        reply_markup=create_time_keyboard(date_str),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_time)
    await callback.answer()

# ====================== Выбор времени (с проверкой до 22:00) ======================
@router.callback_query(F.data.startswith("time_"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    full_dt = callback.data.split("_", 1)[1]
    date_str, time_str = full_dt.split(" ")
    hour = int(time_str.split(":")[0])

    # Проверка: сессия должна заканчиваться до 22:00
    if hour + 1 > 22:   # грубая проверка, можно улучшить позже
        await callback.answer("❌ Слишком позднее время. Последнее возможное время — 21:00", show_alert=True)
        return

    await state.update_data(selected_date=date_str, selected_time=time_str)
    
    await callback.message.edit_text(
        text=f"✅ Выбрано:\n"
             f"📅 Дата: <b>{date_str}</b>\n"
             f"⏰ Время: <b>{time_str}</b>\n\n"
             "⏱ Выбери длительность сессии:",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_duration)
    await callback.answer()

# ====================== Длительность ======================
@router.callback_query(F.data.startswith("duration_"))
async def process_duration(callback: CallbackQuery, state: FSMContext):
    if callback.data == "duration_custom":
        await callback.message.edit_text("Напиши длительность в часах (например: 2 или 4.5):")
        await state.set_state(BookingStates.waiting_for_duration)
        await callback.answer()
        return

    duration = int(callback.data.split("_")[1])
    await state.update_data(duration=duration)

    data = await state.get_data()
    await callback.message.edit_text(
        text=f"✅ Выбрано:\n"
             f"📅 Дата: <b>{data['selected_date']}</b>\n"
             f"⏰ Время: <b>{data['selected_time']}</b>\n"
             f"⏱ Длительность: <b>{duration} час{'а' if duration == 1 else 'ов'}</b>\n\n"
             "🎤 Нужен ли звукорежиссёр? (Да / Нет)",
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_sound_engineer)
    await callback.answer()

@router.message(BookingStates.waiting_for_duration)
async def process_custom_duration(message: Message, state: FSMContext):
    try:
        duration = float(message.text.replace(",", "."))
        if duration < 1: duration = 1
    except:
        await message.answer("Пожалуйста, введи число.")
        return

    await state.update_data(duration=duration)
    data = await state.get_data()

    await message.answer(
        text=f"✅ Выбрано:\n"
             f"📅 Дата: <b>{data['selected_date']}</b>\n"
             f"⏰ Время: <b>{data['selected_time']}</b>\n"
             f"⏱ Длительность: <b>{duration} час{'а' if duration == 1 else 'ов'}</b>\n\n"
             "🎤 Нужен ли звукорежиссёр? (Да / Нет)",
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_sound_engineer)

# ====================== Звукорежиссёр + расчёт стоимости ======================
@router.message(BookingStates.waiting_for_sound_engineer)
async def process_sound_engineer(message: Message, state: FSMContext):
    needs_engineer = message.text.lower() in ["да", "yes", "нужен", "да нужен"]
    await state.update_data(sound_engineer=needs_engineer)

    data = await state.get_data()
    duration = data["duration"]
    full_cost = calculate_cost(duration, needs_engineer)
    prepayment = calculate_prepayment(full_cost)

    await state.update_data(full_cost=full_cost, prepayment=prepayment)

    await message.answer(
        text=f"💰 Полная стоимость: <b>{full_cost} ₽</b>\n"
             f"💸 Предоплата 10%: <b>{prepayment} ₽</b>\n\n"
             "Всё верно? Напиши <b>Да</b> для подтверждения.",
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.waiting_for_payment)

# ====================== Подтверждение ======================
@router.message(BookingStates.waiting_for_payment)
async def confirm_before_payment(message: Message, state: FSMContext):
    if message.text.lower() not in ["да", "yes", "ок", "подтверждаю"]:
        await message.answer("Напиши <b>Да</b>, если всё правильно.")
        return

    data = await state.get_data()
    await message.answer(
        text=f"✅ Бронирование подтверждено!\n\n"
             f"📅 {data['selected_date']} в {data['selected_time']}\n"
             f"⏱ {data['duration']} час{'а' if data['duration']==1 else 'ов'}\n"
             f"🎤 Звукорежиссёр: {'Да' if data.get('sound_engineer') else 'Нет'}\n"
             f"💰 Предоплата: <b>{data['prepayment']} ₽</b>\n\n"
             "Оплата через ЮKassa будет добавлена позже.\n"
             "Для отмены используй /cancel",
        parse_mode="HTML"
    )
    await state.clear()

# ====================== Отмена ======================
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Бронирование отменено.", reply_markup=get_main_menu())

# Кнопка назад
@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📆 Выбери дату записи:", reply_markup=create_calendar())
    await state.set_state(BookingStates.waiting_for_date)
    await callback.answer()