from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from aiogram import Bot
from database import get_all_bookings
from tariffs import get_duration_text

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def send_reminders(bot: Bot):
    """Отправляет напоминания за 24 часа до сессии"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    bookings = await get_all_bookings()

    for b in bookings:
        if b["date"] == tomorrow and b["status"] == "confirmed":
            try:
                engineer_text = "Да" if b["sound_engineer"] else "Нет"
                await bot.send_message(
                    chat_id=b["telegram_id"],
                    text=f"🔔 <b>Напоминание о записи!</b>\n\n"
                         f"Завтра у тебя сессия в студии:\n\n"
                         f"📅 {b['date']} в {b['time']}\n"
                         f"⏱ {get_duration_text(b['duration'])}\n"
                         f"🎤 Звукорежиссёр: {engineer_text}\n\n"
                         f"💸 Не забудь оплатить предоплату: <b>{b['prepayment']} ₽</b>\n\n"
                         f"Для отмены используй /cancel (возврат предоплаты только за 24+ ч.)",
                    parse_mode="HTML"
                )
            except Exception:
                pass


def setup_scheduler(bot: Bot):
    """Запускает планировщик"""
    # Каждый день в 12:00 по Москве отправляем напоминания
    scheduler.add_job(send_reminders, "cron", hour=12, minute=0, args=[bot])
    scheduler.start()
    print("✅ Планировщик напоминаний запущен!")