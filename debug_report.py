import asyncio
import logging
from datetime import datetime
from services.crm_api import SitniksAPI

# ==========================================
# ⚙️ НАСТРОЙКИ ДЛЯ ПРОВЕРКИ
# Укажи дату и статус, которые хочешь проверить
CHECK_DATE_STR = "10.01.2026"  # Формат: ДД.ММ.ГГГГ
CHECK_STATUS = "ТТН сформовано" # Точное название статуса (или часть)
# ==========================================

async def debug_run():
    print(f"\n🕵️ ЗАПУСК ОТЛАДКИ...")
    print(f"📅 Ищем дату события: {CHECK_DATE_STR}")
    print(f"🏷  Ищем статус: {CHECK_STATUS}")
    print("-" * 40)

    # Инициализация API
    crm = SitniksAPI()
    
    # Парсим дату
    target_date = datetime.strptime(CHECK_DATE_STR, "%d.%m.%Y").date()
    
    # 1. Скачиваем массив (как это делает бот)
    print("⏳ Скачиваем заказы за последние 60 дней...")
    raw_orders = await crm._get_all_orders_in_range(days_back=60)
    print(f"📥 Всего получено заказов: {len(raw_orders)}")
    print("-" * 40)

    matches = 0
    near_misses = 0
    
    # 2. Анализируем каждый заказ
    for order in raw_orders:
        o_id = order.get('id')
        o_number = order.get('orderNumber')
        
        # Получаем данные из заказа
        status_obj = order.get('status', {})
        status_title = status_obj.get('title', 'Без статуса')
        
        created = order.get('createdAt', 'N/A')
        updated = order.get('updatedAt', 'N/A')
        completed = order.get('completedAt', 'N/A')

        # Логика определения даты (копия из crm_api.py)
        event_date = crm._get_event_date(order)
        
        # Логика проверки статуса
        is_status_match = CHECK_STATUS.lower() in status_title.lower()
        is_date_match = (event_date == target_date)

        # --- ВЫВОД РЕЗУЛЬТАТОВ ---
        
        # Сценарий А: Полное совпадение (ЭТОТ ЗАКАЗ ПОПАДЕТ В ОТЧЕТ)
        if is_status_match and is_date_match:
            matches += 1
            print(f"✅ [БЕРЕМ] Заказ #{o_number} (ID: {o_id})")
            print(f"   Статус: {status_title}")
            print(f"   Событие: {event_date} (взято из {'completedAt' if order.get('completedAt') else 'updatedAt' if order.get('updatedAt') else 'createdAt'})")
            print(f"   Сумма: {order.get('totalPrice')}")
            print("-" * 20)

        # Сценарий Б: Совпал статус, но НЕ совпала дата (Потенциальная потеря?)
        elif is_status_match:
            near_misses += 1
            print(f"❌ [ДАТА НЕ ТА] Заказ #{o_number}")
            print(f"   Статус: '{status_title}' (совпал)")
            print(f"   Дата события: {event_date} (А мы ищем {target_date})")
            print(f"   [Raw Data] Created: {created} | Updated: {updated}")
            print("-" * 20)

        # Сценарий В: Совпала дата, но НЕ совпал статус (Лишний заказ?)
        elif is_date_match:
            # Раскомментируй, если хочешь видеть заказы с другими статусами за этот день
            # print(f"⚠️ [СТАТУС НЕ ТОТ] Заказ #{o_number} за {event_date}")
            # print(f"   Статус: {status_title} (А мы ищем '{CHECK_STATUS}')")
            # print("-" * 20)
            pass

    print("=" * 40)
    print(f"📊 ИТОГ ПРОВЕРКИ:")
    print(f"✅ Найдено в отчет: {matches} шт.")
    print(f"❌ Совпал статус, но другая дата: {near_misses} шт.")
    print("=" * 40)

if __name__ == "__main__":
    asyncio.run(debug_run())