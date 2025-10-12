from aiogram import types
import json

MESSAGES_FILE = "messages.json"


def load_messages():
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_messages(messages):
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def clear_messages():
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def save_message_to_json(message: types.Message):
    messages = load_messages()
    
    message_data = {
        'message_id': message.message_id,
        'chat_id': message.chat.id,
        'username': message.from_user.username if message.from_user else None,
    }
    
    messages.append(message_data)
    save_messages(messages)
    
    return message_data