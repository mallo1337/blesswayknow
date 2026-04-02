import asyncio
import random
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update, delete

from models import User, Inventory, Ticket, Promo  # Добавь Promo в импорт
from database import init_db, async_session

load_dotenv()
TOKEN = "7670398819:AAGLtbOmBf7Gm-jjYyjn8RuS7qsUhR3cBJM"
ADMIN_GROUP_ID = -1003743459814  # ID группы с темами
ADMIN_ID = 6909945528              # Твой ID для накрутки баланса

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

class Form(StatesGroup):
    waiting_screenshot = State()
    waiting_ticket = State()
    waiting_promo = State()

class AdminResponse(StatesGroup):
    waiting_for_reply_text = State()

# --- КЛАВИАТУРЫ ---
def main_kb():
    kb = InlineKeyboardBuilder()
    # Кнопки в два столбика
    kb.add(types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
    kb.add(types.InlineKeyboardButton(text="📦 Кейсы", callback_data="shop"))
    kb.add(types.InlineKeyboardButton(text="🎒 Инвентарь", callback_data="open_inv"))
    kb.add(types.InlineKeyboardButton(text="🎟 Промокод", callback_data="activate_promo"))
    kb.add(types.InlineKeyboardButton(text="🆘 Тикет", callback_data="new_ticket"))
    kb.adjust(2) # Вот эта магия делает 2 столбика
    return kb.as_markup()

# --- КОМАНДЫ АДМИНА ---
@dp.message(Command("create_promo"))
async def adm_create_promo(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return
    if not command.args: return await message.answer("Юзай: /create_promo КОД СУММА КОЛВО")
    
    args = command.args.split()
    code, reward, uses = args[0], float(args[1]), int(args[2])
    
    async with async_session() as session:
        session.add(Promo(code=code, reward=reward, uses=uses))
        await session.commit()
    await message.answer(f"✅ Промокод `{code}` на {reward} 🌀 создан ({uses} шт.)", parse_mode="Markdown")

# --- ОСНОВНАЯ ЛОГИКА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            session.add(User(tg_id=message.from_user.id, username=message.from_user.username, balance=0))
            await session.commit()
    await message.answer("🦾 Добро пожаловать в **StandRise**!", reply_markup=main_kb(), parse_mode="Markdown")

# --- ПРОМОКОДЫ ---
@dp.callback_query(F.data == "activate_promo")
async def promo_step1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("⌨️ Введите промокод:")
    await state.set_state(Form.waiting_promo)
    await callback.answer()

@dp.message(Form.waiting_promo)
async def promo_step2(message: types.Message, state: FSMContext):
    code = message.text.strip()
    async with async_session() as session:
        res = await session.execute(select(Promo).where(Promo.code == code))
        promo = res.scalar()
        
        if promo and promo.uses > 0:
            user = await session.get(User, message.from_user.id)
            user.balance += promo.reward
            promo.uses -= 1
            if promo.uses <= 0: await session.delete(promo)
            await session.commit()
            await message.answer(f"🎉 Активировано! +{promo.reward} 🌀 на баланс.")
        else:
            await message.answer("❌ Промокод не существует или закончился.")
    await state.clear()

# --- ИНВЕНТАРЬ (2 СТОЛБИКА) ---
@dp.callback_query(F.data == "open_inv")
async def show_inventory(callback: types.CallbackQuery):
    async with async_session() as session:
        res = await session.execute(select(Inventory).where(Inventory.user_id == callback.from_user.id))
        items = res.scalars().all()
        if not items: return await callback.answer("背包 Инвентарь пуст!", show_alert=True)
        
        text = "🎒 **ВАШ ИНВЕНТАРЬ:**\n\n"
        kb = InlineKeyboardBuilder()
        for idx, item in enumerate(items, 1):
            text += f"{idx}. {item.item_name} — {item.item_price} 🌀\n"
            # Группируем кнопки продажи и вывода в одну строку для каждого скина
            kb.row(
                types.InlineKeyboardButton(text=f"💵 Прод. №{idx}", callback_data=f"sell_{item.id}"),
                types.InlineKeyboardButton(text=f"🚚 Выв. №{idx}", callback_data=f"out_{item.id}")
            )
        kb.row(types.InlineKeyboardButton(text="⬅️ В меню", callback_data="back"))
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb.as_markup())

# --- ТИКЕТЫ (ФИКС ДВОЙНОГО НАЖАТИЯ) ---
@dp.callback_query(F.data.startswith("t_"))
async def adm_ticket_action(callback: types.CallbackQuery, state: FSMContext):
    if not callback.message.reply_markup: return await callback.answer("Уже обработано!")
    
    data = callback.data.split("_")
    act, tid = data[1], data[2]

    if act == "acc":
        uid = data[3]
        await state.update_data(reply_uid=uid, reply_tid=tid, topic_id=callback.message.message_thread_id)
        await callback.message.edit_text(f"{callback.message.text}\n\n✅ Взят в работу: {callback.from_user.full_name}", reply_markup=None)
        await callback.message.answer("✍️ Текст ответа:")
        await state.set_state(AdminResponse.waiting_for_reply_text)
    else:
        await callback.message.edit_text(f"{callback.message.text}\n\n❌ Отклонен: {callback.from_user.full_name}", reply_markup=None)
        try: await bot.close_forum_topic(ADMIN_GROUP_ID, callback.message.message_thread_id)
        except: pass
    await callback.answer()

@dp.message(AdminResponse.waiting_for_reply_text)
async def admin_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_text = (f"📩 **ОТВЕТ ПО ТИКЕТУ #1{int(data['reply_tid']):04d}**\n\n"
                 f"Админ ({message.from_user.full_name}) ответил:\n«{message.text}»\n\nСпасибо.")
    try: await bot.send_message(chat_id=int(data['reply_uid']), text=user_text, parse_mode="Markdown")
    except: pass
    try: await bot.close_forum_topic(ADMIN_GROUP_ID, data['topic_id'])
    except: pass
    await state.clear()

# --- ВЫВОД (ФИКС ДВОЙНОГО НАЖАТИЯ) ---
@dp.callback_query(F.data.startswith("adm_"))
async def adm_out_dec(callback: types.CallbackQuery):
    if not callback.message.reply_markup: return await callback.answer("Уже обработано!")
    
    data = callback.data.split("_")
    act, iid, uid = data[1], int(data[2]), int(data[3])
    
    async with async_session() as session:
        item = await session.get(Inventory, iid)
        if act == "ok":
            if item: await session.delete(item)
            try: await bot.send_message(uid, "🎉 Скин выведен!")
            except: pass
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ Выдал: {callback.from_user.full_name}", reply_markup=None)
        else:
            try: await bot.send_message(uid, "❌ Отказ в выводе.")
            except: pass
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ Отклонил: {callback.from_user.full_name}", reply_markup=None)
        await session.commit()
    try: await bot.close_forum_topic(ADMIN_GROUP_ID, callback.message.message_thread_id)
    except: pass
    await callback.answer()

# --- ОСТАЛЬНОЕ (ПРОФИЛЬ, МАГАЗИН, НАЗАД) ---
@dp.callback_query(F.data == "profile")
async def view_profile(callback: types.CallbackQuery):
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        text = (f"👤 **ПРОФИЛЬ**\n\n💰 Баланс: {user.balance} 🌀\n"
                f"📦 Кейсов: {user.cases_count}\n💎 Профит: {user.total_earned} 🌀")
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_kb())

@dp.callback_query(F.data == "shop")
async def shop_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Открыть (10 🌀)", callback_data="buy_case"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    await callback.message.edit_text("🛒 Кейс Standoff 2 за 10 монет:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "buy_case")
async def process_buy(callback: types.CallbackQuery):
    async with async_session() as session:
        user = await session.get(User, callback.from_user.id)
        if user.balance < 10: return await callback.answer("❌ Нет денег!", show_alert=True)
        user.balance -= 10
        user.cases_count += 1
        item = random.choice(STANDOFF_ITEMS)
        user.total_earned += item['price']
        session.add(Inventory(user_id=user.tg_id, item_name=item['name'], item_price=item['price']))
        await session.commit()
        await callback.message.answer(f"🎁 Выпало: {item['name']} ({item['price']} 🌀)")

@dp.callback_query(F.data == "back")
async def cmd_back(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_kb())

@dp.callback_query(F.data.startswith("sell_"))
async def sell_item(callback: types.CallbackQuery):
    iid = int(callback.data.split("_")[1])
    async with async_session() as session:
        item = await session.get(Inventory, iid)
        if item:
            user = await session.get(User, callback.from_user.id)
            user.balance += item.item_price
            await session.delete(item)
            await session.commit()
            await callback.answer(f"Продано за {item.item_price} 🌀")
    await show_inventory(callback)

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())