import asyncio
import os
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from aiohttp import web  # <--- Добавили импорт для веб-сервера

from services.crm_api import SitniksAPI
from formatter import format_order_report

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
crm = SitniksAPI()

# Состояния
class ReportFlow(StatesGroup):
    waiting_for_specific_date = State()
    waiting_for_period = State()
    waiting_for_status = State() 

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📉 Вчера"), KeyboardButton(text="📅 Конкретная дата")],
        [KeyboardButton(text="🗓 За период")]
    ], resize_keyboard=True)

def get_status_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Перевірити обмін"), KeyboardButton(text="Очікує обмін")],
        [KeyboardButton(text="Обмін підтверджено"), KeyboardButton(text="Виконано")],
        [KeyboardButton(text="Відмінено"), KeyboardButton(text="ТТН сформовано")],
        [KeyboardButton(text="Запаковано"), KeyboardButton(text="Відправлено")],
        [KeyboardButton(text="Всі"), KeyboardButton(text="🔙 Отмена")]
    ], resize_keyboard=True)

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() 
    await message.answer("👋 Выберите период:", reply_markup=get_main_kb())

@dp.message(F.text == "🔙 Отмена")
async def global_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=get_main_kb())

@dp.message(F.text == "📉 Вчера")
async def report_yesterday(message: types.Message, state: FSMContext):
    yesterday = (datetime.now() - timedelta(days=1)).date()
    await state.update_data(date_start=yesterday, date_end=yesterday)
    await message.answer("Какой статус фильтровать?", reply_markup=get_status_kb())
    await state.set_state(ReportFlow.waiting_for_status)

@dp.message(F.text == "📅 Конкретная дата")
async def ask_date(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введите дату (ДД.ММ):")
    await state.set_state(ReportFlow.waiting_for_specific_date)

@dp.message(ReportFlow.waiting_for_specific_date)
async def process_date(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip() + f".{datetime.now().year}"
        target_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        await state.update_data(date_start=target_date, date_end=target_date)
        await message.answer("Какой статус фильтровать?", reply_markup=get_status_kb())
        await state.set_state(ReportFlow.waiting_for_status)
    except ValueError:
        await message.answer("⚠️ Ошибка. Нужен формат 10.01")

@dp.message(F.text == "🗓 За период")
async def ask_period(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введите период (ДД.ММ-ДД.ММ):")
    await state.set_state(ReportFlow.waiting_for_period)

@dp.message(ReportFlow.waiting_for_period)
async def process_period(message: types.Message, state: FSMContext):
    try:
        raw = message.text.strip()
        s, e = raw.split("-")
        y = datetime.now().year
        d_start = datetime.strptime(f"{s.strip()}.{y}", "%d.%m.%Y").date()
        d_end = datetime.strptime(f"{e.strip()}.{y}", "%d.%m.%Y").date()
        await state.update_data(date_start=d_start, date_end=d_end)
        await message.answer("Какой статус фильтровать?", reply_markup=get_status_kb())
        await state.set_state(ReportFlow.waiting_for_status)
    except ValueError:
        await message.answer("⚠️ Ошибка. Нужен формат 01.01-05.01")

@dp.message(ReportFlow.waiting_for_status)
async def generate_final_report(message: types.Message, state: FSMContext):
    status_choice = message.text.strip()
    
    if status_choice == "🔙 Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_main_kb())
        return

    data = await state.get_data()
    d_start = data['date_start']
    d_end = data['date_end']
    
    loading_msg = await message.answer(f"⏳ Ищу заказы '{status_choice}' за {d_start}...", reply_markup=types.ReplyKeyboardRemove())
    
    orders = await crm.get_report_orders(d_start, d_end, status_filter=status_choice)
    
    period_str = f"{d_start}" if d_start == d_end else f"{d_start}-{d_end}"
    header_add = f" (Статус: {status_choice})"
    text = format_order_report(orders, period_str + header_add)
    
    try:
        await loading_msg.delete()
    except:
        pass

    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                await message.answer(part, parse_mode="Markdown", reply_markup=get_main_kb())
            else:
                await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_kb())
        
    await state.clear()

# --- ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def keep_alive(request):
    return web.Response(text="I am alive")

async def start_server():
    app = web.Application()
    app.add_routes([web.get('/', keep_alive)])
    runner = web.AppRunner(app)
    await runner.setup()
    # Render автоматически передает PORT. Если нет - берем 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЗАПУСК ---
async def main():
    # Сначала запускаем веб-сервер, чтобы Render увидел открытый порт
    await start_server()
    # Потом запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())