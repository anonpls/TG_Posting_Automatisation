import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import random

from bot import (
    forward_saved_message,
    ADMIN_UNS,
    CHANNEL_CHAT_ID
)

async def post(message_id: int):
    success = await forward_saved_message(message_id, CHANNEL_CHAT_ID)
    return success

async def post_random():
    from bot import messages
    if not messages:
        print("Нет постов для публикации")
        return False
    
    rand_adm = random.choice(ADMIN_UNS)
    print(f"{rand_adm}")
    msg_from_adm = [msg for msg in messages if msg['username'] == rand_adm]
    msg = random.choice(msg_from_adm)

    success = await post(msg['message_id'])
    if success:
        print(f"Пост {msg['message_id']} от {msg['username']} опубликован в канал")
    else:
        print(f"Не удалось опубликовать пост {msg['message_id']}")
    return success

async def periodic_post():
    while True:
        await post_random()
        await asyncio.sleep(5)