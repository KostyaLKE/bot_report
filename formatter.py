# Файл: formatter.py
from datetime import datetime

def format_order_report(orders, period_str, filter_status=""):
    if not orders:
        return f"📅 Период: {period_str}\n❌ Заказов со статусом '{filter_status}' не найдено."

    # Считаем итоги сразу
    total_count = len(orders)
    total_sum = sum(float(o.get('totalPrice', 0)) for o in orders)
    
    # Определяем иконку для заголовка
    icon = "📋"
    if "відправлено" in filter_status.lower(): icon = "🚚"
    elif "виконано" in filter_status.lower(): icon = "💰"

    # === ЗАГОЛОВОК ===
    lines = [
        f"{icon} **ОТЧЕТ: {filter_status.upper()}**",
        f"📅 Дата события: {period_str}",
        f"📊 **Всего заказов: {total_count} шт.**",
        f"💵 **На сумму: {total_sum:,.2f} UAH**".replace(",", " "),
        "──────────────────"
    ]
    
    # === СПИСОК ЗАКАЗОВ ===
    for i, order in enumerate(orders, 1):
        o_id = order.get('orderNumber') or order.get('id')
        
        # Данные из CRM (для сверки)
        crm_status = order.get('status', {}).get('title', 'Неизвестно')
        
        client = order.get('client', {}) or {}
        client_name = client.get('fullname', 'Без имени')
        
        # Товары (кратко)
        products = order.get('products', [])
        # Если товаров много, пишем "Товар А + еще 2..."
        if len(products) > 1:
            prod_str = f"{products[0].get('title')} (+{len(products)-1})"
        elif products:
            prod_str = products[0].get('title')
        else:
            prod_str = "Без товара"
            
        ttn = order.get('delivery', {}).get('billOfLading') or \
              order.get('npDelivery', {}).get('billOfLading') or \
              "-"

        # Компактный блок заказа
        # 1. 1234 | Иванов И.И.
        # 2. Товар... | 1500 UAH
        # 3. ТТН: ... (Статус CRM: ...)
        
        block = (
            f"**{i}. Заказ #{o_id}** | 👤 {client_name}\n"
            f"📦 {prod_str} | 💰 {float(order.get('totalPrice', 0))} грн\n"
            f"🎫 ТТН: `{ttn}`\n"
            f"ℹ️ (В CRM сейчас: {crm_status})"
        )
        lines.append(block)
        lines.append("─ ─ ─ ─ ─") # Легкий разделитель

    return "\n".join(lines)