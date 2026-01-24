# Файл: formatter.py
from datetime import datetime

def format_order_report(orders, period_str, filter_status=""):
    if not orders:
        return f"📅 Период: {period_str}\n❌ Заказов со статусом '{filter_status}' не найдено."

    total_count = len(orders)
    total_sum = sum(float(o.get('totalPrice', 0)) for o in orders)
    
    icon = "📋"
    if "відправлено" in filter_status.lower(): icon = "🚚"
    elif "виконано" in filter_status.lower(): icon = "💰"

    lines = [
        f"{icon} **ОТЧЕТ: {filter_status.upper()}**",
        f"📅 Период: {period_str}",
        f"📊 **Всего заказов: {total_count} шт.**",
        f"💵 **На сумму: {total_sum:,.2f} UAH**".replace(",", " "),
        "──────────────────"
    ]
    
    for i, order in enumerate(orders, 1):
        o_id = order.get('orderNumber') or order.get('id')
        crm_status = order.get('status', {}).get('title', 'Неизвестно')
        
        # Получаем дату сканирования (если есть)
        confirmed_date = order.get('_confirmed_date')
        date_str = confirmed_date.strftime('%d.%m') if confirmed_date else "?"

        client = order.get('client', {}) or {}
        client_name = client.get('fullname', 'Без имени')
        
        # === ЛОГИКА ТОВАРОВ (НОВАЯ) ===
        products = order.get('products', [])
        if products:
            # Собираем список всех названий
            titles = [p.get('title', 'Без названия') for p in products]
            # Объединяем их через перенос строки + иконку
            # Результат будет: "Товар 1\n📦 Товар 2\n📦 Товар 3"
            prod_str = "\n📦 ".join(titles)
        else:
            prod_str = "Без товара"
            
        ttn = order.get('delivery', {}).get('billOfLading') or \
              order.get('npDelivery', {}).get('billOfLading') or \
              "-"

        # === ЛОГИКА СТАТУСОВ ===
        status_info = f"ℹ️ CRM: {crm_status}"
        
        if "відправлено" in filter_status.lower() and "відправлено" not in crm_status.lower():
             status_info = f"⚠️ CRM: {crm_status} (но уехала {date_str})"

        # Формируем блок
        # Цена приклеится к последнему товару, это нормально выглядит
        block = (
            f"**{i}. Заказ #{o_id}** | 👤 {client_name}\n"
            f"📦 {prod_str} | 💰 {float(order.get('totalPrice', 0))} грн\n"
            f"🎫 ТТН: `{ttn}`\n"
            f"{status_info}"
        )
        lines.append(block)
        lines.append("─ ─ ─ ─ ─")

    return "\n".join(lines)