import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Float, select, update

# --- НАСТРОЙКИ (ЗАПОЛНИ СВОИ ДАННЫЕ) ---
TOKEN = "7670398819:AAGLtbOmBf7Gm-jjYyjn8RuS7qsUhR3cBJM"
DB_URL = "postgresql+asyncpg://postgres:zoonyxx123@localhost:5432/case_bot_db"

# --- БАЗА ДАННЫХ ---
engine = create_async_engine(DB_URL)
async_session = async_sessionmaker(engine)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=1000.0) # Даем 1000 для теста
    opened_count: Mapped[int] = mapped_column(default=0)

# Данные кейса (можно менять)
CASE_NAME = "Кейс Чингисхана"
CASE_PRICE = 250
DROPS = [
    {"name": "🗡 Золотая Сабля", "chance": 5},
    {"name": "🏹 Лук Степей", "chance": 25},
    {"name": "🛡 Старый Щит", "chance": 70}
]

# --- ЛОГИКА БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            session.add(User(tg_id=message.from_user.id, username=message.from_user.username))
            await session.commit()
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
    kb.row(types.InlineKeyboardButton(text="📦 Кейсы", callback_data="cases"))
    await message.answer("Добро пожаловать в симулятор кейсов!", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "profile")
async def profile(callback: types.CallbackQuery):
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        text = (f"👤 **Профиль:** {user.username}\n"
                f"🆔 ID: `{user.tg_id}`\n"
                f"💰 Баланс: {user.balance} руб.\n"
                f"📦 Открыто кейсов: {user.opened_count}")
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=callback.message.reply_markup)

@dp.callback_query(F.data == "cases")
async def cases_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text=f"{CASE_NAME} - {CASE_PRICE}₽", callback_data="view_case"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="start_menu"))
    await callback.message.edit_text("Выберите кейс для открытия:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "view_case")
async def view_case(callback: types.CallbackQuery):
    drop_list = "\n".join([f"• **{d['name']}**" for d in DROPS])
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💰 Купить", callback_data="buy_case"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="cases"))
    await callback.message.edit_text(f"📦 **{CASE_NAME}**\n\nСодержимое:\n{drop_list}", 
                                     parse_mode="Markdown", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "buy_case")
async def buy_case(callback: types.CallbackQuery):
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        
        if user.balance < CASE_PRICE:
            return await callback.answer("❌ Недостаточно средств!", show_alert=True)
        
        # Списываем деньги
        user.balance -= CASE_PRICE
        user.opened_count += 1
        await session.commit()

    # Анимация
    msg = callback.message
    frames = ["📦 Открываем...", "🌀 Крутим барабан...", "✨ Почти готово...", "🎁"]
    for frame in frames:
        await msg.edit_text(frame)
        await asyncio.sleep(0.5)

    # Рандом дропа
    res = random.choices(DROPS, weights=[d['chance'] for d in DROPS])[0]
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="⬆️ Апгрейд", callback_data="upg"),
           types.InlineKeyboardButton(text="💵 Продать", callback_data="sell"))
    kb.row(types.InlineKeyboardButton(text="🚚 Вывести", callback_data="withdraw"))
    
    await msg.edit_text(f"🎉 Выпало: **{res['name']}**!", parse_mode="Markdown", reply_markup=kb.as_markup())

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())