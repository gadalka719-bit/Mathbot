import asyncio
import logging
import os
import http.server
import threading
from fractions import Fraction
import sympy as sp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types

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

def calculate_root(number: float, degree: int = 2) -> dict:
    if number < 0 and degree % 2 == 0:
        return {"error": "Нельзя извлечь четный корень из отрицательного числа"}
    return {
        "number": number, "degree": degree,
        "simplified_exact": str(sp.root(sp.nsimplify(number), degree)),
        "approximate_decimal": float(sp.N(sp.root(number, degree), 6))
    }

def calculate_fractions(frac1: str, frac2: str, operation: str) -> dict:
    f1, f2 = Fraction(frac1), Fraction(frac2)
    if operation == "add": res = f1 + f2
    elif operation == "sub": res = f1 - f2
    elif operation == "mul": res = f1 * f2
    elif operation == "div":
        if f2 == 0: return {"error": "Деление на ноль"}
        res = f1 / f2
    else: return {"error": "Неизвестная операция"}
    
    whole = res.numerator // res.denominator if res.numerator >= 0 else -(-res.numerator // res.denominator)
    rem = abs(res.numerator) % res.denominator
    mixed = f"{whole} {rem}/{res.denominator}" if whole != 0 and rem != 0 else str(res)
    
    return {
        "fraction_1": str(f1), "fraction_2": str(f2), "operation": operation,
        "improper_fraction": str(res), "mixed_number": mixed, "decimal": round(float(res), 6)
    }

def evaluate_expression(expression: str) -> dict:
    try:
        expr = sp.sympify(expression)
        return {"simplified": str(sp.simplify(expr)), "numeric_value": str(sp.N(expr, 6))}
    except Exception as e:
        return {"error": str(e)}

math_tools = [calculate_root, calculate_fractions, evaluate_expression]

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
    system_instruction = (
        f"You are an expert, friendly math tutor Telegram bot. "
        f"CRITICAL RULE: You MUST respond strictly in {target_language_name}. "
        f"You calculate LCM (НОК) and GCD (НОД) of numbers accurately and explain step-by-step. "
        f"For roots, fractions, and complex expressions, use the provided Python tools. "
        f"Do NOT use raw LaTeX dollar signs ($)."
    )

    try:
        response = await asyncio.to_thread(
            ai_client.models.generate_content,
            model=MODEL_ID,
            contents=message.text,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=math_tools,
                temperature=0.2,
            )
        )
        await wait_msg.edit_text(response.text or TEXTS[lang]["error"], parse_mode="Markdown")
    except Exception as e:
        logging.error(f"AI Error: {e}")
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
