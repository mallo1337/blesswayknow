# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Указываем путь к .env более надежно
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Если переменная всё равно пустая, выводим ошибку для диагностики
    raise ValueError("Ошибка: DATABASE_URL не найден в .env. Проверьте содержимое файла!")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    from models import User, Inventory, Ticket, Promo
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)