# Файл: services/crm_api.py
import os
import aiohttp
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .novaposhta_api import NovaPoshtaAPI

load_dotenv()

class SitniksAPI:
    def __init__(self):
        self.base_url = os.getenv("CRM_URL", "").rstrip('/')
        self.token = os.getenv("CRM_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        self.np_api = NovaPoshtaAPI()

    async def _get_all_orders_in_range(self, days_back=60):
        """Скачивает заказы с запасом."""
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

    # === РЕЖИМ 1: РАЗВЕДЧИК (LIVE) ===
    # Используется для текущего дня или если данных нет в базе.
    # Делает запросы к Новой Почте.
    async def get_report_orders(self, target_date_start, target_date_end=None, status_filter=None):
        raw_orders = await self._get_all_orders_in_range(days_back=60)
        filtered_orders = []
        
        if not target_date_end:
            target_date_end = target_date_start

        target_status = status_filter.lower() if status_filter else None
        
        # 1. ЛОГИКА "ВІДПРАВЛЕНО" (Через НП)
        if target_status and "відправлено" in target_status:
            # Собираем ТТН
            orders_with_ttn = []
            ttn_list = []
            
            for order in raw_orders:
                ttn = order.get('delivery', {}).get('billOfLading')
                if not ttn:
                    ttn = order.get('npDelivery', {}).get('billOfLading')
                
                if ttn:
                    orders_with_ttn.append((order, ttn))
                    ttn_list.append(ttn)
            
            # Запрашиваем даты у НП
            if ttn_list:
                np_dates = await self.np_api.get_tracking_dates(ttn_list)
                
                for order, ttn in orders_with_ttn:
                    real_date = np_dates.get(ttn)
                    
                    if real_date:
                        if target_date_start <= real_date <= target_date_end:
                            order['_confirmed_date'] = real_date
                            order['_confirmed_event'] = "Фактична відправка (НП)"
                            filtered_orders.append(order)
            
            filtered_orders.sort(key=lambda x: x.get('_confirmed_date', datetime.min.date()))
            return filtered_orders

        # 2. ЛОГИКА "ВИКОНАНО"
        for order in raw_orders:
            if target_status and "виконано" in target_status:
                dt_str = order.get('completedAt')
                if not dt_str and "виконано" in order.get('status', {}).get('title', '').lower():
                    dt_str = order.get('updatedAt')
                
                if dt_str:
                    event_date = datetime.fromisoformat(dt_str.replace('Z', '')).date()
                    if target_date_start <= event_date <= target_date_end:
                        order['_confirmed_date'] = event_date
                        order['_confirmed_event'] = "Закриття угоди"
                        filtered_orders.append(order)
                continue

            # 3. ОСТАЛЬНЫЕ СТАТУСЫ
            current_status = order.get('status', {}).get('title', '').lower()
            if target_status and target_status not in current_status:
                continue

            dt_str = order.get('updatedAt') or order.get('createdAt')
            event_date = datetime.fromisoformat(dt_str.replace('Z', '')).date()
            
            if target_date_start <= event_date <= target_date_end:
                order['_confirmed_date'] = event_date
                order['_confirmed_event'] = "Зміна статусу"
                filtered_orders.append(order)

        filtered_orders.sort(key=lambda x: x.get('_confirmed_date', datetime.min.date()))
        return filtered_orders

    # === РЕЖИМ 2: БИБЛИОТЕКАРЬ (АРХИВ) ===
    # Используется, когда мы уже знаем список нужных ID из базы.
    # НЕ делает запросы к НП (экономит время).
    async def get_orders_by_specific_ids(self, date_obj, target_ids):
        """
        Берет заказы за дату и оставляет только те, что есть в списке target_ids.
        """
        # Берем узкий диапазон дат (дата события +/- 5 дней), чтобы не качать всю базу
        d_start = date_obj - timedelta(days=5)
        d_end = date_obj + timedelta(days=5)
        
        raw_orders = []
        limit = 50
        skip = 0
        
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    'limit': limit,
                    'skip': skip,
                    'dateFrom': d_start.strftime('%Y-%m-%d'),
                    'dateTo': d_end.strftime('%Y-%m-%d')
                }
                url = f"{self.base_url}/orders"
                try:
                    async with session.get(url, headers=self.headers, params=params) as resp:
                        if resp.status != 200: break
                        data = await resp.json()
                        batch = data.get('data', [])
                        if not batch: break
                        raw_orders.extend(batch)
                        if len(batch) < limit: break
                        skip += limit
                except:
                    break
        
        # Фильтруем по списку "золотых" ID
        target_ids_str = [str(i) for i in target_ids]
        filtered = []
        
        for order in raw_orders:
            o_id = str(order.get('orderNumber') or order.get('id'))
            if o_id in target_ids_str:
                # Восстанавливаем метку для красивого отчета
                order['_confirmed_date'] = date_obj
                order['_confirmed_event'] = "Фактична відправка (НП)"
                filtered.append(order)
                
        return filtered