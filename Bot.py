import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

import msgs
import posting

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_CHAT_ID = int(os.getenv('CHANNEL_ID'))
ADMIN_UNS = [admin_id for admin_id in os.getenv('ADMIN_UNS', '').split(',')]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
messages = msgs.load_messages()

def admin_required(func):
    async def wrapper(message):
        if message.from_user.username not in ADMIN_UNS:
            await message.answer("Недостаточно прав для совершения команды.")
            return
        return await func(message)
    return wrapper

def general_admin_required(func):
    async def wrapper(message):
        if message.from_user.username != ADMIN_UNS[0] and message.from_user.username not in ADMIN_UNS:
            await message.answer("Недостаточно прав для совершения команды")
            return
        elif message.from_user.username != ADMIN_UNS[0]:
            await message.answer("Для этой команды требуются права главного админа")
            return
        return await func(message)
    return wrapper

async def forward_saved_message(target_message_id: int, target_chat_id: int):
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
    global messages
    message_data = msgs.save_message_to_json(message)
    messages = msgs.load_messages()
    await message.answer(f"Сообщение сохранено в JSON: ID {message_data['message_id']} от {message_data['username']}")
    print(f"Сообщение сохранено в JSON: ID {message_data['message_id']} от {message_data['username']}")

@dp.message(Command("start"))
@admin_required
async def start_command(message: types.Message):
    await message.answer("Бот запущен и готов к пересылке сообщений!")

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

@dp.message(Command("clear"))
@general_admin_required
async def clear_message(message: types.Message):
    try:
        msgs.clear_messages()
        messages.clear()
        await message.answer(f"База данных очищена")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(Command("info"))
@admin_required
async def info_command(message: types.Message):
    response = "Сохраненные сообщения:\n\n"
    for msg in messages:
        response += f"{msg['message_id']} | {msg['username']}\n"
        response += "─" * 30 + "\n"

    await message.answer(response)

@dp.message(Command("addadm"))
@general_admin_required
async def add_admin(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /addadm @<username>\nПример: /addadm @ivan")
            return

        new_id = args[1][0:]
        if new_id in ADMIN_UNS:
            await message.answer("Этот пользователь уже является админом.")
            return

        ADMIN_UNS.append(new_id)

        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('ADMIN_UNS'):
                    f.write(f"ADMIN_UNS = {','.join(map(str, ADMIN_UNS))}\n")
                else:
                    f.write(line)

        await message.answer(f"Новый админ добавлен: {new_id}")

    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(Command("deladm"))
@general_admin_required
async def add_admin(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Используйте: /deladm @<username>\nПример: /deladm @ivan")
            return

        new_id = args[1][0:]
        if new_id in ADMIN_UNS:
            ADMIN_UNS.remove(new_id)
        else:
            await message.answer("Этот пользователь уже отсутствует в списке админов.")
            return


        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('ADMIN_UNS'):
                    f.write(f"ADMIN_UNS = {','.join(map(str, ADMIN_UNS))}\n")
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
