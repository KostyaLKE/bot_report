# Файл: services/crm_api.py
import os
import aiohttp
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class SitniksAPI:
    def __init__(self):
        self.base_url = os.getenv("CRM_URL", "").rstrip('/')
        self.token = os.getenv("CRM_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    async def _get_all_orders_in_range(self, days_back=60):
        """Скачивает заказы с запасом по времени."""
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days_back)
        
        orders = []
        limit = 50
        skip = 0
        
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    'limit': limit,
                    'skip': skip,
                    'dateFrom': date_from.strftime('%Y-%m-%d'),
                    'dateTo': date_to.strftime('%Y-%m-%d')
                }
                url = f"{self.base_url}/orders"
                try:
                    async with session.get(url, headers=self.headers, params=params) as resp:
                        if resp.status != 200:
                            logging.error(f"API Error {resp.status}: {await resp.text()}")
                            break
                        data = await resp.json()
                        batch = data.get('data', [])
                        if not batch: break
                        orders.extend(batch)
                        if len(batch) < limit: break
                        skip += limit
                except Exception as e:
                    logging.error(f"Connection error: {e}")
                    break
        return orders

    def _get_event_date(self, order):
        """Определяет дату события (закрытия или обновления)."""
        if order.get('completedAt'):
            dt_str = order.get('completedAt')
            return datetime.fromisoformat(dt_str.replace('Z', '')).date()
        if order.get('updatedAt'):
             dt_str = order.get('updatedAt')
             return datetime.fromisoformat(dt_str.replace('Z', '')).date()
        dt_str = order.get('createdAt')
        return datetime.fromisoformat(dt_str.replace('Z', '')).date()

    async def get_report_orders(self, target_date_start, target_date_end=None, status_filter=None):
        """
        status_filter: строка (например 'Відправлено') или None (если нужны все)
        """
        raw_orders = await self._get_all_orders_in_range(days_back=60)
        filtered_orders = []
        
        if not target_date_end:
            target_date_end = target_date_start

        # Нормализация фильтра (приводим к нижнему регистру для сравнения)
        target_status_lower = status_filter.lower() if status_filter and status_filter != "Всі" else None

        for order in raw_orders:
            # 1. Проверка статуса (если выбран фильтр)
            if target_status_lower:
                order_status = order.get('status', {}).get('title', '').lower()
                # Можно использовать in для частичного совпадения или == для точного
                if target_status_lower not in order_status:
                    continue

            # 2. Проверка даты
            event_date = self._get_event_date(order)
            if target_date_start <= event_date <= target_date_end:
                filtered_orders.append(order)

        filtered_orders.sort(key=lambda x: x.get('createdAt', ''))
        return filtered_orders