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

if not TG_TOKEN or not MONO_TOKEN:
    raise Exception("Перевір .env файл — токени не знайдені")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# -------- MONOBANK FUNCTIONS --------

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

# -------- TELEGRAM HANDLERS --------

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

@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = (
        "🤖 Доступні команди:\n"
        "/start — запуск бота\n"
        "/week — витрати за 7 днів\n"
        "/help — ця довідка"
    )
    await message.answer(help_text)

# -------- START BOT --------

async def main():
    print("Бот запущено...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())