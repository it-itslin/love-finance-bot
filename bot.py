import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import gspread
from google.oauth2.service_account import Credentials
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton 

# Получаем секреты
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON") 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция подключения к Google Таблице
def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.sheet1 # Берем первый лист

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # ВСТАВЬ СЮДА СВОЮ ССЫЛКУ ИЗ GITHUB PAGES
    web_app_url = "https://it-itslin.github.io/love-finance-bot/"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть приложение", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "Привет! Я готов записывать твои траты.\nНапиши: `/add 500 Еда`\n\nИли открой красивое приложение:", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    try:
        # Разбираем команду: /add 500 Еда
        text = message.text.split(maxsplit=2)
        amount = text[1]
        category = text[2] if len(text) > 2 else "Без категории"
        
        # Записываем в таблицу: [ID юзера, Сумма, Категория, Дата]
        sheet = get_sheet()
        sheet.append_row([str(message.from_user.id), amount, category, str(message.date)])
        
        await message.answer(f"✅ Записано: {amount} руб. на {category}")
    except Exception as e:
        await message.answer(f"Ошибка при записи: {e}")

async def main():
    print("Бот запущен...")
    # timeout=25, чтобы бот поработал 25 секунд и завершился (не тратил лимиты GitHub)
    await dp.start_polling(bot, timeout=25)

if __name__ == "__main__":
    asyncio.run(main())
