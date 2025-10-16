import sqlite3
from aiogram import types
import os

MESSAGES_DB = "messages.db"


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
            PRIMARY KEY (message_id, chat_id)
        )
    ''')
    conn.commit()
    conn.close()


def load_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, username, current_message_id, posted FROM messages WHERE posted = FALSE')
    rows = cursor.fetchall()
    conn.close()
    return [{'message_id': row[0], 'chat_id': row[1], 'username': row[2], 'current_message_id': row[3], 'posted': bool(row[4])} for row in rows]


def load_all_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, username, current_message_id, posted FROM messages')
    rows = cursor.fetchall()
    conn.close()
    return [{'message_id': row[0], 'chat_id': row[1], 'username': row[2], 'current_message_id': row[3], 'posted': bool(row[4])} for row in rows]


def save_messages(messages):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    for msg in messages:
        cursor.execute('INSERT OR REPLACE INTO messages (message_id, chat_id, username, current_message_id, posted) VALUES (?, ?, ?, ?, ?)',
                       (msg['message_id'], msg['chat_id'], msg['username'], msg.get('current_message_id'), msg.get('posted', False)))
    conn.commit()
    conn.close()


def clear_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    conn.close()


def save_message_to_db(message: types.Message):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO messages (message_id, chat_id, username, posted) VALUES (?, ?, ?, FALSE)',
                   (message.message_id, message.chat.id, message.from_user.username if message.from_user else None))
    conn.commit()
    conn.close()
    
    return {
        'message_id': message.message_id,
        'chat_id': message.chat.id,
        'username': message.from_user.username if message.from_user else None,
        'posted': False
    }


def update_message_posted(message_id, chat_id, current_message_id):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE messages SET current_message_id = ?, posted = TRUE WHERE message_id = ? AND chat_id = ?',
                   (current_message_id, message_id, chat_id))
    conn.commit()
    conn.close()
