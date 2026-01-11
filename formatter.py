def format_order_report(orders, period_str):
    if not orders:
        return "❌ Заказов за этот период (по дате активности) не найдено."

    lines = [f"📊 **РЕЕСТР ЗАКАЗОВ**", f"📆 Период: {period_str}", ""]
    
    total_sum = 0
    count = 0
    
    for order in orders:
        count += 1
        # Извлекаем данные безопасно
        o_id = order.get('orderNumber') or order.get('id')
        status = order.get('status', {}).get('title', 'Неизвестно')
        client = order.get('client', {}) or {}
        client_name = client.get('fullname', 'Без имени')
        client_phone = client.get('phone', 'Нет телефона')
        
        # Цена
        price = order.get('totalPrice', 0)
        total_sum += float(price)
        currency = "UAH" # Или брать из settings
        
        # Товары
        products = order.get('products', [])
        prod_lines = []
        for p in products:
            title = p.get('title', 'Товар')
            qty = p.get('quantity', 1)
            prod_lines.append(f"{title} ({qty} шт)")
        prod_str = ", ".join(prod_lines)
        
        # ТТН
        ttn = "Нет ТТН"
        delivery = order.get('npDelivery', {})
        if delivery and delivery.get('billOfLading'):
            ttn = delivery.get('billOfLading')
        
        # Дата для отображения (берем updatedAt или completedAt)
        date_show = order.get('updatedAt', '')[:10]
        if order.get('completedAt'):
            date_show = order.get('completedAt', '')[:10]

        # Сборка блока
        block = (
            f"🔹 **#{o_id}** | {date_show}\n"
            f"🔎 Статус: {status}\n"
            f"📦 {prod_str}\n"
            f"💰 {price} {currency}\n"
            f"👤 {client_name} | 📞 {client_phone}\n"
            f"🚚 ТТН: `{ttn}`\n"
            f"────────────────"
        )
        lines.append(block)

    # Футер
    lines.append("")
    lines.append(f"∑ **Всего заказов:** {count}")
    lines.append(f"💰 **Общая сумма:** {total_sum:.2f}")

    return "\n".join(lines)