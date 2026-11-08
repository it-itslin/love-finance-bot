import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Токен берется из секретов GitHub
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! 👋\nЯ работаю через GitHub Actions.")

async def main():
    print("Бот проснулся и проверяет сообщения...")
    # timeout=25 означает, что бот поработает 25 секунд и завершится
    await dp.start_polling(bot, timeout=25)

if __name__ == "__main__":
    asyncio.run(main())