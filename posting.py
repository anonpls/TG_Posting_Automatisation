import importlib
from datetime import datetime, time, timedelta
import asyncio
import random
from bot import (
    forward_saved_message,
    get_admin_uns,
    CHANNEL_CHAT_ID
)
from msgs import (
    load_messages
)
from adminstat import (
    add_post_to_count
)


async def post(message_id: int):
    from config import LAST_TIME_POST, POSTING_INTERVAL
    if (datetime.now() - LAST_TIME_POST >= timedelta(hours = POSTING_INTERVAL)):
        success = await forward_saved_message(message_id, CHANNEL_CHAT_ID)
        with open('config.py', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if line.startswith('LAST_TIME_POST'):
                        f.write(f"LAST_TIME_POST = datetime({datetime.now().year}, {datetime.now().month}, {datetime.now().day}, {datetime.now().hour}, {datetime.now().minute}, {datetime.now().second})\n")
                    else:
                        f.write(line)
                f.truncate()
        return success


async def post_random():
    messages = load_messages()
    admins = get_admin_uns()

    if not messages:
        print("Нет постов для публикации")
        return False
    
    rand_adm = random.choice(admins)
    print(f"{rand_adm}")

    msg_from_adm = [msg for msg in messages if msg['username'] == rand_adm]
    try:
        msg = random.choice(msg_from_adm)
        success = await post(msg['message_id'])
        if success:
            add_post_to_count(rand_adm)
        else:
            print(f"Не удалось опубликовать пост {msg['message_id']}")
            return success
    except:
        print("У выбранного админа нет постов заготовленных постов") #если посты у админа кончатся 
        await post_random()


async def periodic_post():
    while True:
        import config
        importlib.reload(config)
        now = datetime.now().time()
        if time(config.START_HOUR, config.START_MINUTE) <= now <= time(config.END_HOUR, config.END_MINUTE):
            await post_random()
            await asyncio.sleep(config.POSTING_INTERVAL * 60 * 60)
        else:
            await asyncio.sleep(60)