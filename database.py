import aiosqlite
from datetime import datetime

DB_NAME = "studio.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                phone TEXT,
                email TEXT,
                created_at TEXT
            )
        """)
        
        # Таблица слотов (свободное время)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,           -- например 2026-04-15
                time TEXT NOT NULL,           -- например 10:00
                duration INTEGER NOT NULL,    -- длительность в часах
                is_booked BOOLEAN DEFAULT 0,
                created_at TEXT
            )
        """)
        
        # Таблица броней
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                slot_id INTEGER,
                sound_engineer BOOLEAN DEFAULT 0,
                phone TEXT,
                telegram_tag TEXT,
                email TEXT,
                comment TEXT,
                amount INTEGER,               -- полная стоимость
                prepayment INTEGER,           -- 10% предоплата
                payment_status TEXT DEFAULT 'pending',
                status TEXT DEFAULT 'confirmed',
                created_at TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (slot_id) REFERENCES slots(id)
            )
        """)
        
        # Таблица администраторов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY
            )
        """)
        
        await db.commit()
        print("✅ База данных успешно создана и инициализирована!")

# Функция для добавления тебя как администратора
async def add_admin(admin_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)", (admin_id,))
        await db.commit()

# Получить соединение с БД (будем использовать позже)
async def get_db():
    return await aiosqlite.connect(DB_NAME)