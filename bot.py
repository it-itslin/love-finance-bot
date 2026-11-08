import asyncio
import os
import json
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON") 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Простое хранилище в памяти (сбросится при перезапуске, но для старта сойдет)
# В будущем здесь будет реальная база данных
user_family = {} 

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

# Генератор случайных кодов для семьи
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = user_family.get(user_id)
    
    # Если у пользователя нет семьи, просим создать
    if not family_id:
        await message.answer("Привет! Сначала создай свою пару командой `/create_family`, или присоединись к существующей: `/join_family КОД`.")
        return

    web_app_url = f"https://it-itslin.github.io/love-finance-bot/?family_id={family_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть приложение", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        f"Привет! Твой код семьи: `{family_id}`\nНапиши: `/add 500 Еда`\n\nОткрыть приложение:", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command("create_family"))
async def cmd_create_family(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in user_family:
        await message.answer(f"У тебя уже есть семья. Твой код: `{user_family[user_id]}`")
        return
        
    new_code = generate_code()
    user_family[user_id] = new_code
    await message.answer(f"✅ Семья создана! Твой код приглашения: `{new_code}`\nОтправь его своей второй половинке, чтобы она ввела команду `/join_family {new_code}`")

@dp.message(Command("join_family"))
async def cmd_join_family(message: types.Message, command: CommandObject):
    user_id = str(message.from_user.id)
    if not command.args:
        await message.answer("Напиши код после команды. Например: `/join_family ABC123`")
        return
        
    code = command.args.upper()
    user_family[user_id] = code
    await message.answer(f"✅ Ты присоединился к семье с кодом `{code}`!")

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = user_family.get(user_id)
    
    if not family_id:
        await message.answer("Сначала создай семью `/create_family` или присоединись `/join_family КОД`")
        return

    try:
        text = message.text.split(maxsplit=2)
        amount = text[1]
        category = text[2] if len(text) > 2 else "Без категории"
        
        sheet = get_sheet()
        # Записываем: [Family_ID, User_ID, Сумма, Категория, Дата]
        sheet.append_row([family_id, user_id, amount, category, str(message.date)])
        
        await message.answer(f"✅ Записано: {amount} руб. на {category}")
    except Exception as e:
        await message.answer(f"Ошибка при записи: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot, timeout=25)

if __name__ == "__main__":
    asyncio.run(main())
