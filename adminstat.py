# from aiogram import Bot, Dispatcher, types
# from aiogram.filters import Command
# import asyncio
# import json
# import os
# import time
# from datetime import datetime

# STATISTICS_FILE = "statistics.json"



# def load_stat():
#     from bot import get_admin_uns
#     try:
#         with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     except FileNotFoundError:
#         return []

# def save_stat(messages):
#     with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
#         json.dump(messages, f, ensure_ascii=False, indent=2)

# def clear_stat():
#     with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
#         json.dump([], f, ensure_ascii=False, indent=2)


# def add_to_count(adm):
#     stats = load_stat()
    
#     stats_data = {
#         'message_id': message.message_id,
#         'chat_id': message.chat.id,
#         'username': message.from_user.username if message.from_user else None,
#     }

#     for st in stats:
#         if st['username'] == adm:
#             st['post_count'] = st['post_count'] + 1
    
#     # if message.photo:
#     #     message_data['message_type'] = 'photo'
#     #     message_data['file_id'] = message.photo[-1].file_id
#     # elif message.document:
#     #     message_data['message_type'] = 'document'
#     #     message_data['file_id'] = message.document.file_id
#     # elif message.video:
#     #     message_data['message_type'] = 'video'
#     #     message_data['file_id'] = message.video.file_id
#     # elif message.audio:
#     #     message_data['message_type'] = 'audio'
#     #     message_data['file_id'] = message.audio.file_id
#     # elif message.voice:
#     #     message_data['message_type'] = 'voice'
#     #     message_data['file_id'] = message.voice.file_id
#     # elif message.sticker:
#     #     message_data['message_type'] = 'sticker'
#     #     message_data['file_id'] = message.sticker.file_id
    
#     messages.append(message_data)
#     save_messages(messages)
    
#     return message_data