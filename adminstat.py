import sqlite3
import os
import logging
from dotenv import load_dotenv
from datetime import datetime
import csv

STATISTICS_DB = "statistics.db"
MESSAGES_DB = "messages.db"

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
            queuedcount INTEGER DEFAULT 0,
            viewstotal INTEGER DEFAULT 0,
            reactionstotal INTEGER DEFAULT 0
        )
    ''')
    cursor.execute(f'ATTACH DATABASE "{MESSAGES_DB}" AS messages')
    admins = get_admin_uns()
    for admin in admins:
        cursor.execute('SELECT COUNT(*) FROM messages WHERE username = ? AND posted = 1', (admin,))
        postcount = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM messages WHERE username = ? AND posted = 0', (admin,))
        queuedcount = cursor.fetchone()[0]
        cursor.execute('INSERT OR REPLACE INTO statistics (username, postcount, queuedcount, viewstotal, reactionstotal) VALUES (?, ?, ?, 0, 0)', (admin, postcount, queuedcount))
    conn.commit()
    conn.close()


def export_admin_stat_csv(stat):
    filename = f"admin_stat_{datetime.now().date()}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter = ';')
        writer.writerow([
            "username",
            "posts",
            "queued",
            "views",
            "reactions"
        ])
        for adm in stat:
            writer.writerow([
                adm["username"],
                adm["postcount"],
                adm["queuedcount"],
                adm["viewstotal"],
                adm["reactionstotal"]
            ])
    return filename


def load_stat():
    init_statistics_db()
    update_views_reactions_count() # проблема может быть здесь
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT username, postcount, queuedcount, viewstotal, reactionstotal FROM statistics')
    rows = cursor.fetchall()
    conn.close()
    return [{'username': row[0], 'postcount': row[1], 'queuedcount': row[2], 'viewstotal': row[3], 'reactionstotal': row[4]} for row in rows]


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

def update_views_reactions_count():
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute(f'ATTACH DATABASE "{MESSAGES_DB}" AS messages')
    cursor.execute('''
        UPDATE statistics
        SET
        viewstotal = COALESCE((
            SELECT SUM(m.views)
            FROM messages.messages m
            WHERE m.username = statistics.username
        ), 0),
        reactionstotal = COALESCE((
            SELECT SUM(m.reactions)
            FROM messages.messages m
            WHERE m.username = statistics.username
        ), 0)
    ''')
    conn.commit()
    conn.close()


def reset_statistics():
    init_statistics_db()
    conn = sqlite3.connect(STATISTICS_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistics SET postcount = 0, queuedcount = 0')
    conn.commit()
    conn.close()
