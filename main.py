import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_ID
from handlers.user_handlers import router as user_router
from database import init_db, add_admin

async def main():
    await init_db()
    await add_admin(ADMIN_ID)
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    dp.include_router(user_router)

    print("🚀 Бот запущен на Railway!")
    print("🗄️ База данных готова")

    await dp.start_polling(bot, polling_timeout=60)

if __name__ == "__main__":
    asyncio.run(main())