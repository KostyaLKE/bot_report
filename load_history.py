# Файл: load_history.py
import asyncio
import logging
from datetime import date, timedelta
from services.crm_api import SitniksAPI
from services.db import init_db, save_daily_stats

# Настройка логов
logging.basicConfig(level=logging.INFO)

# ПЕРИОД ЗАГРУЗКИ
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 1, 12)

async def load_historical_data():
    print("⏳ Инициализация базы данных...")
    init_db()
    
    crm = SitniksAPI()
    
    print(f"🚀 Начинаю загрузку истории с {START_DATE} по {END_DATE}")
    print("-" * 40)

    current_date = START_DATE
    while current_date <= END_DATE:
        print(f"📅 Обрабатываю дату: {current_date}...")
        
        # 1. Запрашиваем "умный" отчет (CRM + API Новой Почты)
        # Бот сам проверит ключи, найдет реальную дату сканирования
        orders = await crm.get_report_orders(current_date, current_date, status_filter="Відправлено")
        
        if orders:
            count = len(orders)
            total_sum = sum(float(o.get('totalPrice', 0)) for o in orders)
            
            # Собираем ID для истории
            ids = [o.get('orderNumber') or o.get('id') for o in orders]
            
            # 2. Сохраняем в БД
            save_daily_stats(current_date, count, total_sum, ids)
            print(f"   ✅ Записано: {count} шт. | {total_sum:,.2f} грн")
        else:
            save_daily_stats(current_date, 0, 0.0, [])
            print(f"   🤷‍♂️ Отправок не найдено.")
            
        print("-" * 40)
        current_date += timedelta(days=1)
        
        # Маленькая пауза, чтобы не дудосить API (хороший тон)
        await asyncio.sleep(0.5)

    print("🏁 Историческая загрузка завершена!")

if __name__ == "__main__":
    asyncio.run(load_historical_data())