import importlib
import logging
import os
import aiohttp
import ssl
import certifi
from datetime import datetime, time, timedelta
import asyncio
import random
from dotenv import load_dotenv
import msgs
from adminstat import (
    get_admin_uns,
    add_post_to_count,
    decrement_queued_to_count
)

load_dotenv(override=True)
CHANNEL_CHAT_ID = int(os.getenv('CHANNEL_ID'))

ssl_context = ssl.create_default_context(cafile=certifi.where())

logger = logging.getLogger(__name__)

new_message_event = asyncio.Event()
is_waiting_for_message = False


async def forward_saved_message(target_message_id: int, target_chat_id: int, admin_username=None):

    messages = msgs.load_messages()
    BOT_MAPPINGS = os.getenv('BOT_MAPPINGS', '')
    bots = {}
    if BOT_MAPPINGS:
        for mapping in BOT_MAPPINGS.split(','):
            if ':' in mapping:
                parts = mapping.split(':')
                if len(parts) >= 2:
                    token = ':'.join(parts[:-1])
                    username = parts[-1]
                    bots[username] = token

    for msg in messages:
        if msg['message_id'] == target_message_id:
            if msg['username'] not in bots:
                try:
                    from bot import bot
                    if msg.get('is_forwarded_from_channel', True):
                        forwarded_msg = await bot.forward_message(
                            chat_id=target_chat_id,
                            from_chat_id=msg['chat_id'],
                            message_id=msg['message_id']
                        )
                    else:
                        forwarded_msg = await bot.copy_message(
                            chat_id=target_chat_id,
                            from_chat_id=msg['chat_id'],
                            message_id=msg['message_id']
                        )

                    logger.info(f"Сообщение {target_message_id} переслано в канал")
                    msgs.update_message_posted(msg['message_id'], msg['chat_id'], forwarded_msg.message_id)
                    return True

                except Exception as e:
                    logger.error(f"Ошибка при пересылке сообщения {target_message_id}: {e}")
                    return False
            else:
                other_bot_token = bots[msg['username']]
                api_url = f"https://api.telegram.org/bot{other_bot_token}"

                try:
                    if msg.get('is_forwarded_from_channel', True):
                        method = "forwardMessage"
                    else:
                        method = "copyMessage"

                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{api_url}/{method}",
                            json={
                                "chat_id": target_chat_id,
                                "from_chat_id": msg['chat_id'],
                                "message_id": msg['message_id'],
                            },
                            ssl=ssl_context
                        ) as response:
                            data = await response.json()

                            if not data.get("ok", False):
                                logger.error(f"Ошибка Telegram API при отправке другим ботом: {data}")
                                return False

                            forwarded_msg_id = data["result"]["message_id"]

                    logger.info(f"Сообщение {target_message_id} отправлено ботом @{msg['username']}")

                    msgs.update_message_posted(
                        msg['message_id'],
                        msg['chat_id'],
                        forwarded_msg_id
                    )

                    return True

                except Exception as e:
                    logger.error(f"Ошибка при отправке другим ботом: {e}")
                    return False


    logger.warning(f"Сообщение {target_message_id} не найдено")
    return False


async def post(message_id: int):
    from config import LAST_TIME_POST, POSTING_INTERVAL
    if (datetime.now() - LAST_TIME_POST >= timedelta(seconds = POSTING_INTERVAL)):
        success = await forward_saved_message(message_id, CHANNEL_CHAT_ID)
        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('LAST_TIME_POST'):
                    f.write(f"LAST_TIME_POST = {datetime.now().isoformat()}\n")
                else:
                    f.write(line)
        return success


async def post_random():
    global is_waiting_for_message
    messages = msgs.load_messages()
    admins = get_admin_uns()

    if not messages:
        if not is_waiting_for_message:
            logger.warning("Нет постов для публикации. Ожидание нового сообщения...")
            is_waiting_for_message = True
        await new_message_event.wait()
        new_message_event.clear()
        is_waiting_for_message = False
        return await post_random()

    BOT_MAPPINGS = os.getenv('BOT_MAPPINGS', '')
    bots = {}
    if BOT_MAPPINGS:
        for mapping in BOT_MAPPINGS.split(','):
            if ':' in mapping:
                parts = mapping.split(':')
                if len(parts) >= 2:
                    token = ':'.join(parts[:-1])
                    username = parts[-1]
                    bots[username] = token

    rand_adm = random.choice(admins)

    if rand_adm in bots:
        logger.info(f"Выбран админ для постинга: {rand_adm}. Используем именного бота")
    else:
        logger.info(f"Выбран админ для постинга: {rand_adm}. Используем основного бота")

    msg_from_adm = [msg for msg in messages if msg['username'] == rand_adm]
    try:
        msg = random.choice(msg_from_adm)
        success = await post(msg['message_id'])
        if success:
            add_post_to_count(rand_adm)
            decrement_queued_to_count(rand_adm)
        else:
            logger.error(f"Не удалось опубликовать пост {msg['message_id']}")
            return success
    except:
        logger.warning("У выбранного админа нет заготовленных постов")
        await post_random()


async def periodic_post():
    while True:
        import config
        importlib.reload(config)
        now = datetime.now().time()
        today = datetime.now().date()
        if (datetime.now() - config.LAST_RESET_DATE).days >= config.RESET_INTERVAL_DAYS:
            from adminstat import reset_statistics
            from msgs import clear_posted_messages
            reset_statistics()
            clear_posted_messages()
            with open('.env', 'r') as f:
                lines = f.readlines()

            with open('.env', 'w') as f:
                for line in lines:
                    if line.startswith('LAST_RESET_DATE'):
                        f.write(f"LAST_RESET_DATE = {today.isoformat()}\n")
                    else:
                        f.write(line)
        if time(config.START_HOUR, config.START_MINUTE) <= now <= time(config.END_HOUR, config.END_MINUTE):
            await post_random()
            await asyncio.sleep(config.POSTING_INTERVAL)
        else:
            await asyncio.sleep(60)
