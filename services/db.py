import sqlite3
import json
import logging
from datetime import datetime

DB_NAME = "bot_stats.db"

def init_db():
    """Создает таблицу, если её нет."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Таблица хранит: дату, кол-во, сумму и список ID заказов (на всякий случай)
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            count INTEGER,
            total_sum REAL,
            order_ids TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("📁 База данных инициализирована.")

def save_daily_stats(date_obj, count, total_sum, order_ids_list):
    """Записывает или обновляет статистику за день."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    date_str = date_obj.strftime("%Y-%m-%d")
    ids_json = json.dumps(order_ids_list) # Сохраняем список ID как текст
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Используем INSERT OR REPLACE, чтобы обновлять данные, если скрипт запустится дважды
    c.execute('''
        INSERT OR REPLACE INTO daily_stats (date, count, total_sum, order_ids, updated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (date_str, count, total_sum, ids_json, now))
    
    conn.commit()
    conn.close()
    logging.info(f"💾 Статистика за {date_str} сохранена: {count} шт. | {total_sum} грн")

def get_stats_for_period(date_start, date_end):
    """
    (На будущее) Получить сохраненную статистику.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT date, count, total_sum FROM daily_stats 
        WHERE date >= ? AND date <= ?
        ORDER BY date
    ''', (date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")))
    rows = c.fetchall()
    conn.close()
    return rows

    # Файл: services/db.py
# ... (код выше оставляем без изменений) ...

def get_saved_ids_for_date(date_obj):
    """
    Возвращает список ID заказов за конкретную дату, если они есть в базе.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    date_str = date_obj.strftime("%Y-%m-%d")
    
    c.execute("SELECT order_ids FROM daily_stats WHERE date = ?", (date_str,))
    row = c.fetchone()
    conn.close()
    
    if row:
        # row[0] это строка "[2107, 2108]", превращаем её обратно в список Python
        try:
            return json.loads(row[0])
        except:
            return []
    return None