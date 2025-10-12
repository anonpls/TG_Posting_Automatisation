import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

import msgs
import posting
from adminstat import (
    get_admin_uns,
    load_stat
)

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
    for msg in messages:
        if msg['message_id'] == target_message_id:
            try:
                await bot.forward_message(
                    chat_id=target_chat_id,
                    from_chat_id=msg['chat_id'],
                    message_id=msg['message_id']
                )
                
                print(f"Сообщение {target_message_id} переслано в канал")
                return True
                
            except Exception as e:
                print(f"Ошибка при пересылке сообщения {target_message_id}: {e}")
                return False
    
    print(f"Сообщение {target_message_id} не найдено")
    return False


@dp.message(lambda message: message.photo and (message.text is None or not message.text.startswith('/')))
@admin_required
async def handle_source_message(message: types.Message):
    message_data = msgs.save_message_to_json(message)
    await message.answer(f"Сообщение сохранено в JSON: ID {message_data['message_id']} от {message_data['username']}")
    print(f"Сообщение сохранено в JSON: ID {message_data['message_id']} от {message_data['username']}")


@dp.message(Command("start"))
@admin_required
async def start_command(message: types.Message):
    await message.answer(
        "Привет, готов к работе! :)\n\n"
        "Вот список моих команд:\n"
        "/start - Запуск бота и отображение списка команд\n"
        "/post <message_id> - Принудительная пересылка сообщения в канал по ID\n"
        "/settime <start_time> <end_time> - Установка времени начала и конца постинга (формат: HH:MM HH:MM)\n"
        "/setinterval <hours> - Установка интервала постинга в часах\n"
        "/stat - Просмотр статистики по админам\n"
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
        llimit = args[1].split(":")
        ulimit = args[2].split(":")
        with open('config.py', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if line.startswith('START_HOUR'):
                        f.write(f"START_HOUR, START_MINUTE = {llimit[0]}, {llimit[1]}\n")
                    elif line.startswith('END_HOUR'):
                        f.write(f"END_HOUR, END_MINUTE = {ulimit[0]}, {ulimit[1]}\n")
                    else:
                        f.write(line)
                f.truncate()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("setinterval"))
@general_admin_required
async def set_time(message: types.Message):
    try:
        args = message.text.split()
        interval = args[1]
        with open('config.py', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if line.startswith('POSTING_INTERVAL'):
                        f.write (f'POSTING_INTERVAL = {interval}\n')
                    else:
                        f.write(line)
                f.truncate()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("stat"))
@general_admin_required
async def stat_command(message: types.Message):
    stat = load_stat()
    response = "Статистика по админам: (юзернейм|посты)\n\n"
    for adm in stat:
        response += f"{adm['username']} | {adm['postcount']}\n"
        response += "─" * 30 + "\n"
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
    messages = msgs.load_messages()
    response = "Сохраненные сообщения:\n\n"
    for msg in messages:
        response += f"{msg['message_id']} | {msg['username']}\n"
        response += "─" * 30 + "\n"

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
async def add_admin(message: types.Message):
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


async def main():
    asyncio.create_task(posting.periodic_post())
    await dp.start_polling(bot)
    print("Бот запущен")


if __name__ == "__main__":
    asyncio.run(main())