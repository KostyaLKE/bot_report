import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Импортируем сервисы
from services.crm_api import SitniksAPI
from services.db import save_daily_stats

async def collect_daily_data(bot):
    """
    Запускается каждый вечер.
    1. Скачивает данные через НП (максимальная точность).
    2. Сохраняет в локальную базу данных.
    Сообщений НЕ шлет.
    """
    logging.info("🕵️ Начинаю сбор ежедневной статистики...")
    crm = SitniksAPI()
    today = datetime.now().date()
    
    # Фильтруем только ОТПРАВКИ (это самое важное для учета)
    # Используем нашу умную логику с проверкой API Новой Почты
    orders = await crm.get_report_orders(today, today, status_filter="Відправлено")
    
    if orders:
        count = len(orders)
        # Считаем сумму, учитывая возможные ошибки в данных (float)
        total_sum = sum(float(o.get('totalPrice', 0)) for o in orders)
        
        # Собираем список ID заказов (чтобы знать, КТО именно уехал)
        ids = [o.get('orderNumber') or o.get('id') for o in orders]
        
        # Сохраняем в БД
        save_daily_stats(today, count, total_sum, ids)
    else:
        logging.info("🤷‍♂️ Сегодня отправок не найдено. Сохраняю нули.")
        save_daily_stats(today, 0, 0.0, [])

def setup_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    
    # Ставим на 23:50 (надеюсь, ноут еще включен?)
    scheduler.add_job(
        collect_daily_data,
        trigger=CronTrigger(hour=23, minute=50),
        kwargs={'bot': bot}
    )
    
    scheduler.start()
    logging.info("✅ Сборщик данных запущен (23:50 каждый день)")