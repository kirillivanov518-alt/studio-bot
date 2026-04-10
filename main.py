import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Бот успешно запущен на Railway!\n\nЭто тестовая версия.")

async def main():
    print("🚀 Бот запущен на Railway")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())