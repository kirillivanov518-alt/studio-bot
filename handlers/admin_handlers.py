from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import get_all_bookings, get_user_bookings, cancel_booking
from tariffs import get_duration_text
from config import ADMIN_ID

router = Router()

ADMIN_IDS = [ADMIN_ID]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def get_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все брони", callback_data="admin_all_bookings")],
        [InlineKeyboardButton(text="📅 Брони на сегодня", callback_data="admin_today_bookings")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
    ])


# ====================== Вход в панель ======================
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У тебя нет доступа к этой команде.")
        return

    await message.answer(
        "🔧 <b>Панель администратора</b>\n\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


# ====================== Все брони ======================
@router.callback_query(F.data == "admin_all_bookings")
async def admin_all_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    bookings = await get_all_bookings()

    if not bookings:
        await callback.message.edit_text(
            "📋 Броней пока нет.",
            reply_markup=get_admin_menu()
        )
        await callback.answer()
        return

    # Показываем последние 10 броней
    text = "📋 <b>Последние брони:</b>\n\n"
    for b in bookings[:10]:
        status_icon = "✅" if b["status"] == "confirmed" else "❌"
        text += (
            f"{status_icon} <b>#{b['id']}</b> — {b['date']} в {b['time']}\n"
            f"👤 {b['client_name']} | 📱 {b['phone']}\n"
            f"⏱ {get_duration_text(b['duration'])} | "
            f"🎤 {'Да' if b['sound_engineer'] else 'Нет'}\n"
            f"💰 {b['amount']} ₽ (пред. {b['prepayment']} ₽)\n"
            f"──────────────\n"
        )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


# ====================== Брони на сегодня ======================
@router.callback_query(F.data == "admin_today_bookings")
async def admin_today_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    all_bookings = await get_all_bookings()
    bookings = [b for b in all_bookings if b["date"] == today]

    if not bookings:
        await callback.message.edit_text(
            f"📅 На сегодня ({today}) броней нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
            ])
        )
        await callback.answer()
        return

    text = f"📅 <b>Брони на сегодня ({today}):</b>\n\n"
    for b in bookings:
        text += (
            f"⏰ <b>{b['time']}</b> — {get_duration_text(b['duration'])}\n"
            f"👤 {b['client_name']} | 📱 {b['phone']}\n"
            f"🎤 Звукарь: {'Да' if b['sound_engineer'] else 'Нет'}\n"
            f"💰 {b['amount']} ₽\n"
            f"──────────────\n"
        )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


# ====================== Статистика ======================
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    bookings = await get_all_bookings()
    total = len(bookings)
    confirmed = len([b for b in bookings if b["status"] == "confirmed"])
    cancelled = len([b for b in bookings if b["status"] == "cancelled"])
    total_revenue = sum(b["amount"] for b in bookings if b["status"] == "confirmed")
    total_prepayment = sum(b["prepayment"] for b in bookings if b["status"] == "confirmed")

    await callback.message.edit_text(
        text=f"📊 <b>Статистика:</b>\n\n"
             f"📋 Всего броней: <b>{total}</b>\n"
             f"✅ Подтверждённых: <b>{confirmed}</b>\n"
             f"❌ Отменённых: <b>{cancelled}</b>\n\n"
             f"💰 Общая выручка: <b>{total_revenue} ₽</b>\n"
             f"💸 Предоплат получено: <b>{total_prepayment} ₽</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ])
    )
    await callback.answer()


# ====================== Назад ======================
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "🔧 <b>Панель администратора</b>\n\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )
    await callback.answer()