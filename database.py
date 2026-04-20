import aiosqlite
from datetime import datetime

DB_NAME = "studio.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                phone TEXT,
                email TEXT,
                name TEXT,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                username TEXT,
                client_name TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                duration REAL NOT NULL,
                sound_engineer BOOLEAN DEFAULT 0,
                phone TEXT,
                email TEXT,
                comment TEXT,
                amount INTEGER,
                prepayment INTEGER,
                payment_status TEXT DEFAULT 'pending',
                status TEXT DEFAULT 'confirmed',
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY
            )
        """)

        await db.commit()
        print("✅ База данных инициализирована!")


async def save_booking(
    telegram_id: int,
    username: str,
    date: str,
    time: str,
    duration: float,
    sound_engineer: bool,
    phone: str,
    email: str,
    client_name: str,
    comment: str,
    amount: int,
    prepayment: int
) -> int:
    """Сохранить бронь и вернуть её ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Сохраняем/обновляем пользователя
        await db.execute("""
            INSERT INTO users (telegram_id, username, phone, email, name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                phone=excluded.phone,
                email=excluded.email,
                name=excluded.name
        """, (telegram_id, username, phone, email, client_name, datetime.now().isoformat()))

        # Сохраняем бронь
        cursor = await db.execute("""
            INSERT INTO bookings
            (telegram_id, username, client_name, date, time, duration,
             sound_engineer, phone, email, comment, amount, prepayment,
             payment_status, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'confirmed', ?)
        """, (
            telegram_id, username, client_name, date, time, duration,
            sound_engineer, phone, email, comment, amount, prepayment,
            datetime.now().isoformat()
        ))

        await db.commit()
        return cursor.lastrowid


async def get_user_bookings(telegram_id: int) -> list:
    """Получить все брони пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM bookings
            WHERE telegram_id = ?
            ORDER BY date DESC, time DESC
        """, (telegram_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def is_slot_taken(date: str, time: str) -> bool:
    """Проверить занят ли слот"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT id FROM bookings
            WHERE date = ? AND time = ? AND status = 'confirmed'
        """, (date, time))
        row = await cursor.fetchone()
        return row is not None


async def add_admin(admin_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)", (admin_id,))
        await db.commit()


async def get_all_bookings() -> list:
    """Получить все брони (для админа)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM bookings
            ORDER BY date DESC, time DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]