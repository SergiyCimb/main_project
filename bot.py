import asyncio
import requests
import time
import os
from dotenv import load_dotenv
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

TG_TOKEN = os.getenv("TG_TOKEN")
MONO_TOKEN = os.getenv("MONO_TOKEN")

MCC_CATEGORIES = {
    "Продукти": [5411, 5422, 5441],
    "Транспорт": [4111, 4121, 4131],
    "Розваги": [5815, 5816, 5817, 5818],
}

if not TG_TOKEN or not MONO_TOKEN:
    raise Exception("Перевір .env файл — токени не знайдені")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# -------- MONOBANK FUNCTIONS --------

def calculate_categories(transactions):
    categories = {
        "Продукти": 0,
        "Транспорт": 0,
        "Розваги": 0,
        "Інше": 0
    }

    for t in transactions:
        if t["amount"] < 0:
            amount = abs(t["amount"]) / 100
            mcc = t.get("mcc", 0)

            found = False
            for category, mcc_list in MCC_CATEGORIES.items():
                if mcc in mcc_list:
                    categories[category] += amount
                    found = True
                    break

            if not found:
                categories["Інше"] += amount

    return categories

def get_client_info():
    headers = {"X-Token": MONO_TOKEN}
    url = "https://api.monobank.ua/personal/client-info"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    return response.json()

def get_transactions(account_id, days=7):
    headers = {"X-Token": MONO_TOKEN}
    to_time = int(time.time())
    from_time = to_time - days * 86400
    url = f"https://api.monobank.ua/personal/statement/{account_id}/{from_time}/{to_time}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return []

    return response.json()

def calculate_average(transactions, days=7):
    total = 0

    for t in transactions:
        if t["amount"] < 0:
            total += abs(t["amount"]) / 100

    avg = total / days
    return total, avg

def forecast_month(avg_per_day):
    return avg_per_day * 30

# -------- TELEGRAM HANDLERS --------

@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = (
        "🤖 Доступні команди:\n"
        "/start — запуск бота\n"
        "/week — витрати за 7 днів\n" \
        "/categories — витрати по категоріях\n"
        "/avg — середні витрати\n"
        "/forecast — прогноз на місяць\n"
        "/help — ця довідка"
    )
    await message.answer(help_text)

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("✅ Бот працює!\nНапиши /week щоб побачити витрати за 7 днів")

@dp.message(Command("week"))
async def week_handler(message: Message):
    client_info = get_client_info()
    if not client_info:
        await message.answer("❌ Помилка підключення до Monobank")
        return
    account_id = client_info["accounts"][0]["id"]
    transactions = get_transactions(account_id)
    total = 0
    for t in transactions:
        if t["amount"] < 0:
            total += abs(t["amount"])
    total = total / 100
    await message.answer(f"💸 Витрати за 7 днів: {total:.2f} грн")

@dp.message(Command("avg"))
async def avg_handler(message: Message):
    client_info = get_client_info()

    if not client_info:
        await message.answer("❌ Помилка Monobank")
        return

    account_id = client_info["accounts"][0]["id"]
    transactions = get_transactions(account_id, days=7)

    total, avg = calculate_average(transactions)

    text = (
        f"📊 Статистика за 7 днів:\n\n"
        f"💸 Загальні витрати: {total:.2f} грн\n"
        f"📉 Середні витрати: {avg:.2f} грн/день"
    )

    await message.answer(text)

@dp.message(Command("forecast"))
async def forecast_handler(message: Message):
    client_info = get_client_info()

    if not client_info:
        await message.answer("❌ Помилка Monobank")
        return

    account_id = client_info["accounts"][0]["id"]
    transactions = get_transactions(account_id, days=7)

    total, avg = calculate_average(transactions)
    forecast = forecast_month(avg)

    text = (
        f"🔮 Прогноз витрат:\n\n"
        f"📉 Середнє за день: {avg:.2f} грн\n"
        f"📅 Прогноз на місяць: {forecast:.2f} грн"
    )

    await message.answer(text)

@dp.message(Command("categories"))
async def categories_handler(message: Message):
    client_info = get_client_info()

    if not client_info:
        await message.answer("❌ Помилка Monobank")
        return

    account_id = client_info["accounts"][0]["id"]
    transactions = get_transactions(account_id)

    data = calculate_categories(transactions)

    text = "📊 Витрати за категоріями (7 днів):\n\n"

    for cat, amount in data.items():
        text += f"{cat}: {amount:.2f} грн\n"

    await message.answer(text)

# -------- START BOT --------

async def main():
    print("Бот запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())