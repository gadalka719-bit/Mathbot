import asyncio
import logging
import os
import http.server
import threading

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai

# Ключі
TELEGRAM_TOKEN = "9157017403:AAFZrDew8URDf8__d6fNrmY70yU89wauZGo"
GEMINI_API_KEY = "AQ.Ab8RN6J9G0OaWDWf5kt6kSwMrwR5B_eKmaETlOX6BG"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

ai_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.0-flash"

user_languages = {}

TEXTS = {
    "ru": {
        "choose_lang": "🌐 Выберите язык интерфейса / Оберіть мову / Choose language:",
        "welcome": (
            "👋 Привет! Я умный математический бот под управлением ИИ (в облаке 24/7).\n\n"
            "Я умею:\n"
            "• Находить **НОК** и **НОД** любых чисел\n"
            "• Вычислять и упрощать **корни**\n"
            "• Складывать, вычитать, умножать и делить **дроби**\n"
            "• Решать уравнения и объяснять любые задачи\n\n"
            "Просто напиши мне задачу своими словами! Сменить язык: /lang"
        ),
        "thinking": "🤔 Считаю...",
        "error": "❌ Произошла ошибка при вычислении. Попробуй переформулировать запрос."
    },
    "uk": {
        "choose_lang": "🌐 Оберіть мову інтерфейсу:",
        "welcome": (
            "👋 Привіт! Я розумний математичний бот під керуванням ШІ (у хмарі 24/7).\n\n"
            "Я вмію:\n"
            "• Знаходити **НСК** та **НСД** будь-яких чисел\n"
            "• Обчислювати та спрощувати **корені**\n"
            "• Додавати, віднімати, множити та ділити **дроби**\n"
            "• Розв'язувати рівняння та пояснювати будь-які задачі\n\n"
            "Просто напиши мені задачу своїми словами! Змінити мову: /lang"
        ),
        "thinking": "🤔 Рахую...",
        "error": "❌ Сталася помилка під час обчислення. Спробуй переформулювати запит."
    },
    "en": {
        "choose_lang": "🌐 Choose your interface language:",
        "welcome": (
            "👋 Hi! I am an AI-powered smart math bot (in the cloud 24/7).\n\n"
            "I can:\n"
            "• Find **LCM** and **GCD** of any numbers\n"
            "• Calculate and simplify **roots**\n"
            "• Add, subtract, multiply, and divide **fractions**\n"
            "• Solve equations and explain any math problem\n\n"
            "Just type your problem in plain text! Change language: /lang"
        ),
        "thinking": "🤔 Calculating...",
        "error": "❌ An error occurred during calculation. Please try rephrasing your request."
    }
}

LANG_NAMES = {
    "ru": "Russian (Русский)",
    "uk": "Ukrainian (Українська)",
    "en": "English"
}

def get_lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="set_lang_uk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(TEXTS["ru"]["choose_lang"], reply_markup=get_lang_keyboard())

@dp.message(Command("lang"))
async def cmd_lang(message: types.Message):
    lang = user_languages.get(message.from_user.id, "ru")
    await message.answer(TEXTS[lang]["choose_lang"], reply_markup=get_lang_keyboard())

@dp.callback_query(F.data.startswith("set_lang_"))
async def process_lang_select(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[-1]
    user_languages[callback.from_user.id] = lang_code
    await callback.message.edit_text(TEXTS[lang_code]["welcome"], parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text)
async def handle_math_query(message: types.Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")
    target_language_name = LANG_NAMES[lang]

    wait_msg = await message.answer(TEXTS[lang]["thinking"])
    
    prompt = (
        f"You are an expert, friendly math tutor Telegram bot. "
        f"You must respond strictly in {target_language_name}. "
        f"User query: {message.text}. "
        f"Calculate accurately, find LCM/GCD if requested, and explain step-by-step. Do not use raw LaTeX."
    )

    try:
        response = ai_client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        answer_text = response.text if response and response.text else TEXTS[lang]["error"]
        await wait_msg.edit_text(answer_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"AI Error details: {e}")
        try:
            await wait_msg.edit_text(TEXTS[lang]["error"])
        except Exception:
            pass

class DummyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = http.server.HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
