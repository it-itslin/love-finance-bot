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
    except Exception:
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

# ФУНКЦИЯ СОЗДАНИЯ ФАЙЛА data.json (чтобы приложение могло читать данные)
def update_json_file():
    try:
        sheet = get_spreadsheet().sheet1
        rows = sheet.get_all_values()
        data = {}
        # Группируем траты по ID семьи
        for row in rows[1:]:
            fam_id = row[0]
            if fam_id not in data:
                data[fam_id] = []
            data[fam_id].append({
                "user_id": row[1],
                "amount": row[2],
                "category": row[3],
                "date": row[4]
            })
        
        # Записываем в файл
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("Файл data.json успешно обновлен.")
    except Exception as e:
        print(f"Ошибка обновления data.json: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = get_user_family(user_id)
    
    if not family_id:
        await message.answer("Привет! Сначала создай свою пару командой `/create_family`, или присоединись: `/join_family КОД`.")
        return

    # Обновляем данные перед тем как дать ссылку
    update_json_file()

    web_app_url = f"https://it-itslin.github.io/love-finance-bot/?family_id={family_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Открыть приложение", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        f"Твой код семьи: `{family_id}`\nДанные обновлены. Открывай приложение:", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ПРИЕМ ДАННЫХ ИЗ WEB APP (Кнопка "+")
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    user_id = str(message.from_user.id)
    
    try:
        sheet = get_spreadsheet().sheet1
        sheet.append_row([
            data['family_id'], 
            user_id, 
            data['amount'], 
            data['category'], 
            str(message.date)
        ])
        
        # Обновляем json-файл для следующих просмотров
        update_json_file()
        
        await message.answer(f"✅ Через приложение записано: {data['amount']} руб. на «{data['category']}»")
    except Exception as e:
        await message.answer(f"Ошибка записи: {e}")

@dp.message(Command("create_family"))
async def cmd_create_family(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = get_user_family(user_id)
    if family_id:
        await message.answer(f"У тебя уже есть семья. Код: `{family_id}`")
        return
    new_code = generate_code()
    save_user_family(user_id, new_code)
    await message.answer(f"✅ Семья создана! Код: `{new_code}`")

@dp.message(Command("join_family"))
async def cmd_join_family(message: types.Message, command: CommandObject):
    user_id = str(message.from_user.id)
    if not command.args:
        await message.answer("Напиши код после команды.")
        return
    code = command.args.upper()
    save_user_family(user_id, code)
    await message.answer(f"✅ Ты присоединился к семье `{code}`!")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot, timeout=25)

if __name__ == "__main__":
    asyncio.run(main())
