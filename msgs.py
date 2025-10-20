import sqlite3
import logging
from aiogram import types
import os

MESSAGES_DB = "messages.db"

logger = logging.getLogger(__name__)


def init_messages_db():
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            current_message_id INTEGER,
            posted BOOLEAN DEFAULT FALSE,
            is_forwarded_from_channel BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (message_id, chat_id)
        )
    ''')
    conn.commit()
    conn.close()


def load_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, username, current_message_id, posted, is_forwarded_from_channel FROM messages WHERE posted = FALSE')
    rows = cursor.fetchall()
    conn.close()
    return [{'message_id': row[0], 'chat_id': row[1], 'username': row[2], 'current_message_id': row[3], 'posted': bool(row[4]), 'is_forwarded_from_channel': bool(row[5])} for row in rows]


def load_all_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, username, current_message_id, posted, is_forwarded_from_channel FROM messages')
    rows = cursor.fetchall()
    conn.close()
    return [{'message_id': row[0], 'chat_id': row[1], 'username': row[2], 'current_message_id': row[3], 'posted': bool(row[4]), 'is_forwarded_from_channel': bool(row[5])} for row in rows]


def save_messages(messages):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    for msg in messages:
        cursor.execute('INSERT OR REPLACE INTO messages (message_id, chat_id, username, current_message_id, posted, is_forwarded_from_channel) VALUES (?, ?, ?, ?, ?, ?)',
                       (msg['message_id'], msg['chat_id'], msg['username'], msg.get('current_message_id'), msg.get('posted', False), msg.get('is_forwarded_from_channel', False)))
    conn.commit()
    conn.close()


def clear_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    conn.close()


def clear_posted_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE posted = TRUE')
    conn.commit()
    conn.close()
    logger.info("Опубликованные сообщения удалены из базы данных")


def save_message_to_db(message: types.Message):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    is_forwarded_from_channel = message.forward_origin is not None and hasattr(message.forward_origin, 'chat') and message.forward_origin.chat.type in ['channel']
    cursor.execute('INSERT OR IGNORE INTO messages (message_id, chat_id, username, posted, is_forwarded_from_channel) VALUES (?, ?, ?, FALSE, ?)',
                   (message.message_id, message.chat.id, message.from_user.username if message.from_user else None, is_forwarded_from_channel))
    conn.commit()
    conn.close()

    from adminstat import add_queued_to_count
    if message.from_user and message.from_user.username:
        add_queued_to_count(message.from_user.username)
        logger.info(f"Сообщение {message.message_id} сохранено в базу данных от пользователя {message.from_user.username}")

    return {
        'message_id': message.message_id,
        'chat_id': message.chat.id,
        'username': message.from_user.username if message.from_user else None,
        'posted': False,
        'is_forwarded_from_channel': is_forwarded_from_channel
    }


def update_message_posted(message_id, chat_id, current_message_id):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE messages SET current_message_id = ?, posted = TRUE WHERE message_id = ? AND chat_id = ?',
                   (current_message_id, message_id, chat_id))
    conn.commit()
    conn.close()
