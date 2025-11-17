import os
import logging
import aiohttp
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import ssl
import certifi

import msgs
import posting
from adminstat import (
    get_admin_uns,
    load_stat
)

ssl_context = ssl.create_default_context(cafile=certifi.where())

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
logger = logging.getLogger(__name__)

load_dotenv(override=True)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_CHAT_ID = int(os.getenv('CHANNEL_ID'))
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def admin_required(func):
    async def wrapper(message):
        if message.from_user.username not in get_admin_uns():
            await message.answer("Недостаточно прав для совершения команды.")
            return
        return await func(message)
    return wrapper


def general_admin_required(func):
    async def wrapper(message):
        if message.from_user.username != get_admin_uns()[0] and message.from_user.username not in get_admin_uns():
            await message.answer("Недостаточно прав для совершения команды")
            return
        elif message.from_user.username != get_admin_uns()[0]:
            await message.answer("Для этой команды требуются права главного админа")
            return
        return await func(message)
    return wrapper


async def forward_saved_message(target_message_id: int, target_chat_id: int):
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
                logger.info("Используем основного бота")
                try:
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
                logger.info("Используем именного бота")
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


@dp.message(lambda message: (message.photo or message.document or message.video) and (message.text is None or not message.text.startswith('/')))
@admin_required
async def handle_source_message(message: types.Message):
    message_data = msgs.save_message_to_db(message)
    await message.answer(f"Сообщение сохранено в базе данных: ID {message_data['message_id']} от {message_data['username']}")
    logger.info(f"Сообщение сохранено в базе данных: ID {message_data['message_id']} от {message_data['username']}")


@dp.message(Command("menu"))
@admin_required
async def menu_command(message: types.Message):
    await message.answer(
        "Привет, готов к работе! :)\n\n"
        "Вот список моих команд:\n"
        "/menu - Отображение списка команд\n"
        "/post <message_id> - Принудительная пересылка сообщения в канал по ID\n"
        "/settime <start_time> <end_time> - Установка времени начала и конца постинга (формат: HH:MM HH:MM)\n"
        "/setinterval <hours> - Установка интервала постинга в часах\n"
        "/resetstattime <days> - Установка интервала сброса статистики в днях\n"
        "/stat - Просмотр статистики по админам\n"
        "/config - Просмотр текущих настроек конфигурации\n"
        "/clear - Очистка базы данных сообщений\n"
        "/info - Просмотр сохраненных сообщений\n"
        "/addadm @<username> - Добавление нового админа\n"
        "/deladm @<username> - Удаление админа"
    )


@dp.message(Command("post"))
@general_admin_required
async def post_message(message: types.Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "Используйте: /post <message_id>\n\n"
                "Пример: /post 123\n"
                "Список сообщений: /info"
            )
            return
        
        message_id = int(args[1])
        success = await posting.post(message_id)
        
        if success:
            await message.answer(f"Сообщение {message_id} переслано в канал")
        else:
            await message.answer(f"Не удалось переслать сообщение {message_id}")
            
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("settime"))
@general_admin_required
async def set_time(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer("Используйте: /settime <start_time> <end_time>\nПример: /settime 09:00 18:00")
            return
        llimit = args[1].split(":")
        ulimit = args[2].split(":")
        if len(llimit) != 2 or len(ulimit) != 2:
            await message.answer("Неверный формат времени. Используйте HH:MM")
            return
        start_hour, start_min = int(llimit[0]), int(llimit[1])
        end_hour, end_min = int(ulimit[0]), int(ulimit[1])
        if not (0 <= start_hour <= 23 and 0 <= start_min <= 59 and 0 <= end_hour <= 23 and 0 <= end_min <= 59):
            await message.answer("Время должно быть в диапазоне 00:00 - 23:59")
            return
        start_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        if start_time >= end_time:
            await message.answer("Время начала должно быть меньше времени конца")
            return
        with open('config.py', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if line.startswith('START_HOUR'):
                        f.write(f"START_HOUR, START_MINUTE = {start_hour}, {start_min}\n")
                    elif line.startswith('END_HOUR'):
                        f.write(f"END_HOUR, END_MINUTE = {end_hour}, {end_min}\n")
                    else:
                        f.write(line)
                f.truncate()
        await message.answer(f"Время постинга установлено: {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}")
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("setinterval"))
@general_admin_required
async def set_interval(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /setinterval <hours>\nПример: /setinterval 2")
            return
        interval = int(args[1])
        if interval <= 0:
            await message.answer("Интервал должен быть положительным числом")
            return
        with open('config.py', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if line.startswith('POSTING_INTERVAL'):
                        f.write (f'POSTING_INTERVAL = {interval}\n')
                    else:
                        f.write(line)
                f.truncate()
        await message.answer(f"Интервал постинга установлен: {interval} часов")
    except ValueError:
        await message.answer("Интервал должен быть целым числом")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("resetstattime"))
@general_admin_required
async def set_reset_stat_time(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /resetstattime <days>\nПример: /resetstattime 7")
            return
        days = int(args[1])
        if days <= 0:
            await message.answer("Интервал должен быть положительным числом")
            return
        with open('config.py', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if line.startswith('RESET_INTERVAL_DAYS'):
                        f.write(f"RESET_INTERVAL_DAYS = {days}\n")
                    else:
                        f.write(line)
                f.truncate()
        await message.answer(f"Интервал сброса статистики установлен: {days} дней")
    except ValueError:
        await message.answer("Интервал должен быть целым числом")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("stat"))
@general_admin_required
async def stat_command(message: types.Message):
    stat = load_stat()
    response = "Статистика по админам: (юзернейм|выложенные|в очереди)\n\n"
    for adm in stat:
        response += f"{adm['username']} | {adm['postcount']} | {adm['queuedcount']}\n"
        response += "─" * 40 + "\n"
    await message.answer(response)


@dp.message(Command("config"))
@general_admin_required
async def config_command(message: types.Message):
    import config
    admins = get_admin_uns()
    response = "Текущие настройки конфигурации:\n\n"
    response += f"Время начала постинга: {config.START_HOUR:02d}:{config.START_MINUTE:02d}\n"
    response += f"Время конца постинга: {config.END_HOUR:02d}:{config.END_MINUTE:02d}\n"
    if config.POSTING_INTERVAL >= 1:
        response += f"Интервал постинга: {round(config.POSTING_INTERVAL)} часов\n"
    elif config.POSTING_INTERVAL >= 1/60:
        minutes = round(config.POSTING_INTERVAL * 60)
        response += f"Интервал постинга: {minutes} минут\n"
    else:
        seconds = round(config.POSTING_INTERVAL * 3600)
        response += f"Интервал постинга: {seconds} секунд\n"
    response += f"Последний пост: {config.LAST_TIME_POST}\n"
    response += f"Последний сброс статистики: {config.LAST_RESET_DATE}\n"
    response += f"Интервал сброса статистики: {config.RESET_INTERVAL_DAYS} дней\n"
    response += f"Админы: {', '.join('@' + adm for adm in admins)}\n"
    await message.answer(response)


@dp.message(Command("clear"))
@general_admin_required
async def clear_message(message: types.Message):
    try:
        msgs.clear_messages()
        await message.answer(f"База данных очищена")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("info"))
@admin_required
async def info_command(message: types.Message):
    messages = msgs.load_all_messages()
    response = "Сохраненные сообщения:\n\n"
    for msg in messages:
        status = "Опубликовано" if msg['posted'] else "Не опубликовано"
        response += f"{msg['message_id']} | {msg['username']} | {status}\n"
        response += "─" * 40 + "\n"

    await message.answer(response)


@dp.message(Command("addadm"))
@general_admin_required
async def add_admin(message: types.Message):
    try:
        admins = get_admin_uns()
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /addadm @<username>\nПример: /addadm @ivan")
            return

        new_id = args[1][1:]
        if new_id in admins:
            await message.answer("Этот пользователь уже является админом.")
            return

        admins.append(new_id)

        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('ADMIN_UNS'):
                    f.write(f"ADMIN_UNS = {','.join(map(str, admins))}\n")
                else:
                    f.write(line)

        await message.answer(f"Новый админ добавлен: {new_id}")

    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("deladm"))
@general_admin_required
async def del_admin(message: types.Message):
    try:
        admins = get_admin_uns()
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /deladm @<username>\nПример: /deladm @ivan")
            return

        new_id = args[1][1:]
        if new_id in admins:
            admins.remove(new_id)
        else:
            await message.answer("Этот пользователь уже отсутствует в списке админов.")
            return


        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('ADMIN_UNS'):
                    f.write(f"ADMIN_UNS = {','.join(map(str, admins))}\n")
                else:
                    f.write(line)

        await message.answer(f"Пользователь {new_id} лишён прав админа.")

    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("addbot"))
@general_admin_required
async def add_bot(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer("Используйте: /addbot <BOT_TOKEN> <USER_TAG>\nПример: /addbot 123456:ABC-DEF... @ivan")
            return

        bot_token = args[1]
        user_tag = args[2].lstrip('@')

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
        
        if user_tag in bots:
            await message.answer(f"Бот для пользователя {user_tag} уже существует.")
            return

        # Обновить .env
        with open('.env', 'r') as f:
            lines = f.readlines()

        bot_mappings = []
        for line in lines:
            if line.startswith('BOT_MAPPINGS'):
                existing = line.split('=')[1].strip()
                if existing:
                    bot_mappings = existing.split(',')
                break
        else:
            lines.append('BOT_MAPPINGS =\n')

        bot_mappings.append(f'{bot_token}:{user_tag}')

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('BOT_MAPPINGS'):
                    f.write(f'BOT_MAPPINGS = {",".join(bot_mappings)}\n')
                else:
                    f.write(line)

        await message.answer(f"Бот для пользователя {user_tag} добавлен.")

    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("deletebot"))
@general_admin_required
async def delete_bot(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /deletebot <USER_TAG>\nПример: /deletebot @ivan")
            return

        user_tag = args[1].lstrip('@')

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

        if user_tag not in bots:
            await message.answer(f"Бот для пользователя {user_tag} не найден.")
            return

        # Обновить .env
        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('BOT_MAPPINGS'):
                    existing = line.split('=')[1].strip()
                    if existing:
                        mappings = [m for m in existing.split(',') if not m.endswith(f':{user_tag}')]
                        f.write(f'BOT_MAPPINGS = {",".join(mappings)}\n')
                    else:
                        f.write('BOT_MAPPINGS =\n')
                else:
                    f.write(line)

        await message.answer(f"Бот для пользователя {user_tag} удалён.")

    except Exception as e:
        await message.answer(f"Ошибка: {e}")


async def main():
    asyncio.create_task(posting.periodic_post())
    await dp.start_polling(bot)
    logger.info("Бот запущен")


if __name__ == "__main__":
    asyncio.run(main())