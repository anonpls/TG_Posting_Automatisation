import sqlite3
import os
from dotenv import load_dotenv

STATISTICS_DB = "statistics.db"


def get_admin_uns():
    load_dotenv(override=True)
    ADMIN_UNS = [admin_id for admin_id in os.getenv('ADMIN_UNS', '').split(',')]
    return ADMIN_UNS


def init_statistics_db():
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            username TEXT PRIMARY KEY,
            postcount INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def migrate_statistics_from_json():
    import json
    if os.path.exists("statistics.json"):
        try:
            with open("statistics.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            conn = sqlite3.connect(STATISTICS_DB)
            cursor = conn.cursor()
            for item in data:
                cursor.execute('INSERT OR REPLACE INTO statistics (username, postcount) VALUES (?, ?)',
                               (item['username'], item['postcount']))
            conn.commit()
            conn.close()
            os.rename("statistics.json", "statistics.json.backup")
        except Exception as e:
            print(f"Error migrating statistics: {e}")


def load_stat():
    init_statistics_db()
    migrate_statistics_from_json()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT username, postcount FROM statistics')
    rows = cursor.fetchall()
    conn.close()
    return [{'username': row[0], 'postcount': row[1]} for row in rows]


def save_stat(stat):
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    for item in stat:
        cursor.execute('INSERT OR REPLACE INTO statistics (username, postcount) VALUES (?, ?)',
                       (item['username'], item['postcount']))
    conn.commit()
    conn.close()


def add_post_to_count(admin):
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistics SET postcount = postcount + 1 WHERE username = ?', (admin,))
    conn.commit()
    conn.close()
