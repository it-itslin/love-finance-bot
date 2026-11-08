import asyncio
import os
import json
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON") 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_spreadsheet():
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

def get_user_family(user_id):
    try:
        ws = get_spreadsheet().worksheet("Users")
        records = ws.get_all_values()
        for row in records[1:]:
            if row[0] == str(user_id):
                return row[1]
        return None
    except Exception as e:
        print(f"Ошибка чтения Users: {e}")
        return None

def save_user_family(user_id, family_id):
    try:
        ws = get_spreadsheet().worksheet("Users")
        records = ws.get_all_values()
        for i, row in enumerate(records[1:], start=2):
            if row[0] == str(user_id):
                ws.update_cell(i, 2, family_id)
                return
        ws.append_row([str(user_id), family_id])
    except Exception as e:
        print(f"Ошибка записи Users: {e}")

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def update_json_file():
    try:
        sheet = get_spreadsheet().sheet1
        rows = sheet.get_all_values()
        data = {}
        for row in rows[1:]:
            if len(row) < 5: continue
            fam_id = row[0]
            if fam_id not in data:
                data[fam_id] = []
            data[fam_id].append({
                "user_id": row[1],
                "amount": row[2],
                "category": row[3],
                "date": row[4]
            })
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Файл data.json успешно обновлен.")
    except Exception as e:
        print(f"ОШИБКА при обновлении data.json: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = get_user_family(user_id)
    
    if not family_id:
        await message.answer("Привет! Сначала создай семью: `/create_family`, или присоединись: `/join_family КОД`.")
        return

    update_json_file() # Обновляем данные перед выдачей ссылки

    web_app_url = f"https://it-itslin.github.io/love-finance-bot/?family_id={family_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть приложение", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(f"Код семьи: `{family_id}`\nОткрывай приложение:", reply_markup=keyboard, parse_mode="Markdown")

# Ловим данные от кнопки "+" в Web App
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = str(message.from_user.id)
        fam_id = data.get('family_id')
        
        if not fam_id:
            await message.answer("Ошибка: не передан ID семьи.")
            return
            
        sheet = get_spreadsheet().sheet1
        sheet.append_row([fam_id, user_id, data.get('amount', '0'), data.get('category', 'Без категории'), str(message.date)])
        update_json_file()
        await message.answer(f"✅ Записано: {data.get('amount')} руб. на «{data.get('category')}»")
    except Exception as e:
        await message.answer(f"Ошибка при записи: {e}")

@dp.message(Command("create_family"))
async def cmd_create_family(message: types.Message):
    user_id = str(message.from_user.id)
    if get_user_family(user_id):
        await message.answer("У тебя уже есть семья.")
        return
    new_code = generate_code()
    save_user_family(user_id, new_code)
    await message.answer(f"✅ Семья создана! Код: `{new_code}`")

@dp.message(Command("join_family"))
async def cmd_join_family(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer("Напиши код: `/join_family ABC123`")
        return
    save_user_family(str(message.from_user.id), command.args.upper())
    await message.answer(f"✅ Присоединился к семье `{command.args.upper()}`!")

async def main():
    print("Бот запущен...")
    update_json_file() # Пробуем обновить при старте
    
    # Запускаем опрос в фоне ровно на 30 секунд
    polling_task = asyncio.create_task(dp.start_polling(bot))
    await asyncio.sleep(30)
    polling_task.cancel()
    
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
        
    print("Бот завершил работу.")
    update_json_file() # Сохраняем финальный результат

if __name__ == "__main__":
    asyncio.run(main())
