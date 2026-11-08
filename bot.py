import asyncio
import os
import json
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import gspread
from google.oauth2.service_account import Credentials

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON") 
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID") 

# Хранилище состояний (в памяти)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Состояния для добавления траты
class AddExpense(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()

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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = get_user_family(user_id)
    
    if not family_id:
        await message.answer("Привет! Сначала создай свою пару командой `/create_family`, или присоединись к существующей: `/join_family КОД`.")
        return

    web_app_url = f"https://it-itslin.github.io/love-finance-bot/?family_id={family_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить трату", callback_data="add_expense")],
        [InlineKeyboardButton(text="📊 Открыть приложение", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        f"Привет! Твой код семьи: `{family_id}`\nВыбери действие:", 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# --- ЛОГИКА ДОБАВЛЕНИЯ ТРАТЫ ---

@dp.callback_query(F.data == "add_expense")
async def process_add_expense(callback: types.CallbackQuery, state: FSMContext):
    # Проверяем, есть ли у юзера семья
    family_id = get_user_family(str(callback.from_user.id))
    if not family_id:
        await callback.message.answer("Сначала создай семью!")
        return
        
    await callback.message.answer("Введи сумму траты (только цифры):")
    await state.set_state(AddExpense.waiting_for_amount)

@dp.message(AddExpense.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи только число (например, 500).")
        return
        
    # Сохраняем сумму в состояние
    await state.update_data(amount=message.text)
    
    # Показываем клавиатуру с категориями
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Еда", callback_data="cat_Еда")],
        [InlineKeyboardButton(text="🚗 Транспорт", callback_data="cat_Транспорт")],
        [InlineKeyboardButton(text="🎬 Развлечения", callback_data="cat_Развлечения")],
        [InlineKeyboardButton(text="🏠 Жилье", callback_data="cat_Жилье")],
        [InlineKeyboardButton(text="💊 Здоровье", callback_data="cat_Здоровье")]
    ])
    
    await message.answer("Выбери категорию:", reply_markup=keyboard)
    await state.set_state(AddExpense.waiting_for_category)

@dp.callback_query(AddExpense.waiting_for_category, F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    user_data = await state.get_data()
    amount = user_data['amount']
    
    user_id = str(callback.from_user.id)
    family_id = get_user_family(user_id)
    
    try:
        # Записываем в Google Таблицу
        sheet = get_spreadsheet().sheet1
        sheet.append_row([family_id, user_id, amount, category, str(callback.message.date)])
        
        await callback.message.edit_text(f"✅ Записано: {amount} руб. на «{category}»")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка записи: {e}")
    
    # Сбрасываем состояние
    await state.clear()

# --- ОСТАЛЬНЫЕ КОМАНДЫ ---
@dp.message(Command("create_family"))
async def cmd_create_family(message: types.Message):
    user_id = str(message.from_user.id)
    family_id = get_user_family(user_id)
    if family_id:
        await message.answer(f"У тебя уже есть семья. Твой код: `{family_id}`")
        return
    new_code = generate_code()
    save_user_family(user_id, new_code)
    await message.answer(f"✅ Семья создана! Твой код: `{new_code}`\nОтправь его партнеру: `/join_family {new_code}`")

@dp.message(Command("join_family"))
async def cmd_join_family(message: types.Message, command: CommandObject):
    user_id = str(message.from_user.id)
    if not command.args:
        await message.answer("Напиши код после команды. Например: `/join_family ABC123`")
        return
    code = command.args.upper()
    save_user_family(user_id, code)
    await message.answer(f"✅ Ты присоединился к семье с кодом `{code}`!")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot, timeout=25)

if __name__ == "__main__":
    asyncio.run(main())
