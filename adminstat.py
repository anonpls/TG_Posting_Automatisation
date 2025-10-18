import sqlite3
import os
import logging
from dotenv import load_dotenv

STATISTICS_DB = "statistics.db"

logger = logging.getLogger(__name__)


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
            postcount INTEGER DEFAULT 0,
            queuedcount INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute('ALTER TABLE statistics ADD COLUMN queuedcount INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
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
            logger.error(f"Error migrating statistics: {e}")


def load_stat():
    init_statistics_db()
    migrate_statistics_from_json()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT username, postcount, queuedcount FROM statistics')
    rows = cursor.fetchall()
    conn.close()
    return [{'username': row[0], 'postcount': row[1], 'queuedcount': row[2]} for row in rows]


def save_stat(stat):
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    for item in stat:
        cursor.execute('INSERT OR REPLACE INTO statistics (username, postcount, queuedcount) VALUES (?, ?, ?)',
                       (item['username'], item['postcount'], item.get('queuedcount', 0)))
    conn.commit()
    conn.close()


def add_post_to_count(admin):
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistics SET postcount = postcount + 1 WHERE username = ?', (admin,))
    conn.commit()
    conn.close()


def add_queued_to_count(admin):
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistics SET queuedcount = queuedcount + 1 WHERE username = ?', (admin,))
    conn.commit()
    conn.close()


def decrement_queued_to_count(admin):
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistics SET queuedcount = queuedcount - 1 WHERE username = ? AND queuedcount > 0', (admin,))
    conn.commit()
    conn.close()


def reset_statistics():
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistics SET postcount = 0, queuedcount = 0')
    conn.commit()
    conn.close()
