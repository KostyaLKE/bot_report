# Файл: services/novaposhta_api.py
import os
import aiohttp
import logging
from datetime import datetime

class NovaPoshtaAPI:
    def __init__(self):
        self.api_keys = []
        i = 1
        while True:
            key = os.getenv(f"NP_KEY_{i}")
            if not key:
                break
            self.api_keys.append(key)
            i += 1
            
        if not self.api_keys and os.getenv("NP_API_KEY"):
            self.api_keys.append(os.getenv("NP_API_KEY"))

        self.url = "https://api.novaposhta.ua/v2.0/json/"

    def _parse_date(self, date_str):
        if not date_str: return None
        formats = ["%H:%M %d.%m.%Y", "%d-%m-%Y %H:%M:%S", "%d.%m.%Y %H:%M:%S", 
                   "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except ValueError: continue
        try: return datetime.strptime(str(date_str)[:10], "%d-%m-%Y").date()
        except: pass
        return None

    async def get_tracking_dates(self, ttn_list):
        if not self.api_keys: return {}
        final_results = {}
        pending_ttns = set(ttn_list)

        for api_key in self.api_keys:
            if not pending_ttns: break
            current_batch_list = list(pending_ttns)
            found_data = await self._query_chunked(api_key, current_batch_list)
            for ttn, date_val in found_data.items():
                final_results[ttn] = date_val
                if ttn in pending_ttns: pending_ttns.remove(ttn)
        return final_results

    async def _query_chunked(self, api_key, ttn_list):
        chunk_size = 100
        results = {}
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(ttn_list), chunk_size):
                chunk = ttn_list[i:i + chunk_size]
                documents = [{"DocumentNumber": ttn, "Phone": ""} for ttn in chunk]
                payload = {
                    "apiKey": api_key,
                    "modelName": "TrackingDocument",
                    "calledMethod": "getStatusDocuments",
                    "methodProperties": {"Documents": documents}
                }
                try:
                    async with session.post(self.url, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('success'):
                                for item in data.get('data', []):
                                    number = item.get('Number')
                                    
                                    # === ЛОГИКА V4 (БРОНЕБІЙНА) ===
                                    
                                    # 1. ПЕРЕВІРКА СТАТУСУ
                                    # Код 1 = "Нова пошта очікує надходження" (Тільки створено)
                                    status_code = item.get('StatusCode')
                                    if str(status_code) == "1":
                                        continue # Це просто папірець, ігноруємо!

                                    # 2. Отримуємо дати
                                    date_scan_str = item.get('DateScan')
                                    date_create_str = item.get('DateCreated')
                                    
                                    if not date_scan_str:
                                        continue 
                                    
                                    dt_scan = self._parse_date(date_scan_str)
                                    dt_create = self._parse_date(date_create_str)
                                    
                                    if dt_scan and dt_create:
                                        # 3. ПЕРЕВІРКА СВІЖОСТІ (Щоб прибрати "привидів" з минулого місяця)
                                        delta = (dt_scan - dt_create).days
                                        if delta > 2:
                                            continue
                                        
                                        # Якщо пройшли всі фільтри - це реальна відправка
                                        results[number] = dt_create
                                    elif dt_scan:
                                        results[number] = dt_scan

                        else:
                            logging.error(f"NP HTTP Error: {resp.status}")
                except Exception as e:
                    logging.error(f"NP Connection Error: {e}")
        return results