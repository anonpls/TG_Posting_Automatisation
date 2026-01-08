import sqlite3
import logging
from aiogram import types
import os
from telethon import TelegramClient
from dotenv import load_dotenv
import csv
from datetime import datetime
import adminstat

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
            views INTEGER DEFAULT 0,
            reactions INTEGER DEFAULT 0,
            PRIMARY KEY (message_id, chat_id)
        )
    ''')
    try:
        cursor.execute('ALTER TABLE messages ADD COLUMN media_group INTEGER DEFAULT NULL')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def get_media_group_ids(mg_id):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id FROM messages WHERE media_group = ?', 
                   (mg_id,))
    rows = cursor.fetchall()
    print(rows)
    conn.close()
    return [row[0] for row in rows]


def export_msgs_csv(stat):
    filename = f"msgs_{datetime.now().date()}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter = ';')
        writer.writerow([
            "message_id",
            "current_message_id",
            "username",
            "views",
            "reactions",
            "posted"
        ])
        for msg in stat:
            writer.writerow([
                msg["message_id"],
                msg["current_message_id"],
                msg["username"],
                msg["views"],
                msg["reactions"],
                msg["posted"]
            ])
    return filename


def load_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, username, current_message_id, posted, is_forwarded_from_channel, views, reactions, media_group FROM messages WHERE posted = FALSE')
    rows = cursor.fetchall()
    conn.close()
    return [{'message_id': row[0], 'chat_id': row[1], 'username': row[2], 'current_message_id': row[3], 'posted': bool(row[4]), 'is_forwarded_from_channel': bool(row[5]), 'views': row[6], 'reactions': row[7], 'media_group': row[8]} for row in rows]


def load_all_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT message_id, chat_id, username, current_message_id, posted, is_forwarded_from_channel, views, reactions, media_group FROM messages')
    rows = cursor.fetchall()
    conn.close()
    return [{'message_id': row[0], 'chat_id': row[1], 'username': row[2], 'current_message_id': row[3], 'posted': bool(row[4]), 'is_forwarded_from_channel': bool(row[5]), 'views': row[6], 'reactions': row[7], 'media_group': row[8]} for row in rows]


def save_messages(messages):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    for msg in messages:
        cursor.execute('INSERT OR REPLACE INTO messages (message_id, chat_id, username, current_message_id, posted, is_forwarded_from_channel, views, reactions) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (msg['message_id'], msg['chat_id'], msg['username'], msg.get('current_message_id'), msg.get('posted', False), msg.get('is_forwarded_from_channel', False), msg.get('views', 0), msg.get('reactions', 0), msg.get('media_group', None)))
    conn.commit()
    conn.close()


def clear_messages():
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    conn.close()


def clear_message(msg_id, adm):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE message_id = ? AND username = ?', 
                   (msg_id, adm))
    num = cursor.rowcount
    conn.commit()
    conn.close()
    return num


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

    media_group_mode = adminstat.get_media_group_mode(message.from_user.username)
    if hasattr(message, 'media_group_id') and media_group_mode:
        media_group_id = message.media_group_id
        mgid = f' - медиа группа {media_group_id}'
    else: media_group_id = None; mgid = ''

    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    is_forwarded_from_channel = message.forward_origin is not None and hasattr(message.forward_origin, 'chat') and message.forward_origin.chat.type in ['channel']
    cursor.execute('INSERT OR IGNORE INTO messages (message_id, chat_id, username, posted, is_forwarded_from_channel, views, reactions, media_group) VALUES (?, ?, ?, FALSE, ?, ?, ?, ?)',
                   (message.message_id, message.chat.id, message.from_user.username, is_forwarded_from_channel, 0, 0, media_group_id))
    conn.commit()
    conn.close()

    if message.from_user and message.from_user.username:
        adminstat.add_queued_to_count(message.from_user.username)
        logger.info(f"Сообщение {message.message_id}{mgid} сохранено в базу данных от пользователя {message.from_user.username}")

    return {
        'message_id': message.message_id,
        'chat_id': message.chat.id,
        'username': message.from_user.username,
        'posted': False,
        'is_forwarded_from_channel': is_forwarded_from_channel,
        'views': 0, 
        'reactions': 0,
        'media_group': media_group_id
    }


def update_message_posted(message_id, chat_id, current_message_id):
    init_messages_db()
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute('UPDATE messages SET current_message_id = ?, posted = TRUE WHERE message_id = ? AND chat_id = ?',
                   (current_message_id, message_id, chat_id))
    conn.commit()
    conn.close()
    logger.info(f'Сообщение {message_id} обновлено как опубликованное с новым ID {current_message_id}')


async def collect_message_stats():
    load_dotenv(override=True)
    api_id = os.getenv('CORE_API_ID')
    api_hash = os.getenv('CORE_API_HASH')
    channel_id = int(os.getenv('CHANNEL_ID'))

    if not api_id or not api_hash:
        logger.error("CORE_API_ID or CORE_API_HASH not found in .env")
        return
    try:
        async with TelegramClient('session', int(api_id), api_hash) as client:
            init_messages_db()
            conn = sqlite3.connect(MESSAGES_DB)
            cursor = conn.cursor()
            cursor.execute('SELECT message_id, chat_id, current_message_id FROM messages WHERE posted = TRUE AND current_message_id IS NOT NULL')
            published_messages = cursor.fetchall()
            conn.close()

            for msg_id, chat_id, current_msg_id in published_messages:
                try:
                    message = await client.get_messages(channel_id, ids=current_msg_id)
                    if message:
                        views = getattr(message, 'views', 0) or 0
                        reactions_count = 0
                        if hasattr(message, 'reactions') and message.reactions:
                            reactions_count = sum(r.count for r in message.reactions.results) if message.reactions.results else 0

                        conn = sqlite3.connect(MESSAGES_DB)
                        cursor = conn.cursor()
                        cursor.execute('UPDATE messages SET views = ?, reactions = ? WHERE message_id = ? AND chat_id = ?',
                                    (views, reactions_count, msg_id, chat_id))
                        conn.commit()
                        conn.close()
                        logger.info(f"Updated stats for message {current_msg_id}: views={views}, reactions={reactions_count}")
                    else:
                        logger.warning(f"Message {current_msg_id} not found in channel")
                except Exception as e:
                    logger.error(f"Error fetching stats for message {current_msg_id}: {e}")
    except:
        logger.error("CORE_API_ID or CORE_API_HASH not found in .env")
