import re
import requests
import xml.etree.ElementTree as ET
import telebot
import openpyxl
import json
import random

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ────────────────────────────────────────────────
# НАСТРОЙКИ
# ────────────────────────────────────────────────

TOKEN = "8788332837:AAF2q6OGaWGspYn20LNtU88a3hy9M5Ubq94"
ADMIN_ID = 6513083324

SCAMALYTICS_USERNAME = "69bdf63b38ccb"
SCAMALYTICS_API_KEY  = "08e94b47a9822258611bd7b9d7e111f5cfb424c8b93b19d59ae33bc574fef216"
SCAMALYTICS_BASE_URL = f"https://api12.scamalytics.com/v3/{SCAMALYTICS_USERNAME}"

bot = telebot.TeleBot(TOKEN)
user_mode = {}

# ────────────────────────────────────────────────
# СОХРАНЕНИЕ ДАННЫХ (НОМЕРА + ПРОГРЕСС)
# ────────────────────────────────────────────────

numbers_list = []
current_index = 0

def save_data():
    with open("numbers_data.json", "w") as f:
        json.dump({
            "numbers": numbers_list,
            "index": current_index
        }, f)

def load_data():
    global numbers_list, current_index
    try:
        with open("numbers_data.json", "r") as f:
            data = json.load(f)
            numbers_list = data.get("numbers", [])
            current_index = data.get("index", 0)
    except:
        numbers_list = []
        current_index = 0

load_data()

# ────────────────────────────────────────────────
# ЗАГРУЗКА EXCEL (ТОЛЬКО АДМИН)
# ────────────────────────────────────────────────

@bot.message_handler(content_types=['document'])
def handle_file(message):
    global numbers_list, current_index

    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Только админ может загружать файл")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open("numbers.xlsx", "wb") as f:
        f.write(downloaded_file)

    wb = openpyxl.load_workbook("numbers.xlsx")
    sheet = wb.active

    numbers_list = []
    current_index = 0

    for row in sheet.iter_rows(min_row=2, values_only=True):
        number = str(row[0]).strip()
        if number:
            numbers_list.append(number)

    save_data()

    bot.reply_to(message, f"✅ Загружено номеров: {len(numbers_list)}")

# ────────────────────────────────────────────────
# ВЫДАЧА НОМЕРОВ
# ────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📲 Получить номер")
def give_number(message):
    global current_index

    if not numbers_list:
        bot.reply_to(message, "❌ Список номеров пуст")
        return

    if current_index >= len(numbers_list):
        bot.reply_to(message, "⚠️ Номера закончились")
        return

    number = numbers_list[current_index]
    current_index += 1

    save_data()

    bot.reply_to(message, f"📞 Ваш номер:\n{number}")

# ────────────────────────────────────────────────
# ГЕНЕРАТОР СЛОВ (API + fallback)
# ────────────────────────────────────────────────

fallback_words = [
    "apple", "river", "dream", "light", "shadow",
    "forest", "ocean", "sky", "storm", "fire"
]

def get_random_word():
    try:
        r = requests.get("https://random-word-api.herokuapp.com/word", timeout=5)
        if r.status_code == 200:
            return r.json()[0]
    except:
        pass

    # fallback если API умер
    return random.choice(fallback_words)

@bot.message_handler(func=lambda m: m.text == "🎲 Генератор слова")
def generate_word(message):
    word = get_random_word()
    bot.reply_to(message, f"🎲 Случайное слово:\n\n👉 {word}")

# ────────────────────────────────────────────────
# ПРОВЕРКИ
# ────────────────────────────────────────────────

def extract_emails(text):
    return re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)

def check_email(email):
    try:
        url = f"https://apis.farahexperiences.com/v1/identity/ZeroBounce/?email={email}"
        response = requests.get(url, timeout=8)
        text = response.text.strip().lower()

        if "true" in text:
            return True
        elif "false" in text:
            return False
        return None
    except:
        return None

def check_ip_fraud(ip):
    try:
        r = requests.get(SCAMALYTICS_BASE_URL, params={
            "key": SCAMALYTICS_API_KEY,
            "ip": ip
        }, timeout=10)

        data = r.json()
        score = data.get("scamalytics", {}).get("scamalytics_score", -1)

        if score >= 90:
            risk = "🔴 Very High"
        elif score >= 60:
            risk = "🟠 High"
        elif score >= 20:
            risk = "🟡 Medium"
        else:
            risk = "🟢 Low"

        return f"{risk} ({score})", None

    except Exception as e:
        return None, str(e)

# ────────────────────────────────────────────────
# КНОПКИ
# ────────────────────────────────────────────────

def get_main_reply_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📧 Чекер почты", "🌐 Чекер IP")
    markup.add("📲 Получить номер", "🎲 Генератор слова")
    markup.add("🔄 Сменить режим")
    return markup

def get_mode_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📧 Почты", callback_data="mode_email"),
        InlineKeyboardButton("🌐 IP", callback_data="mode_ip")
    )
    return markup

# ────────────────────────────────────────────────
# ОСНОВНЫЕ ХЕНДЛЕРЫ
# ────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_mode[message.from_user.id] = None

    bot.send_message(
        message.chat.id,
        "👋 Бот: чекер + номера + генератор слов",
        reply_markup=get_main_reply_keyboard()
    )

    bot.send_message(message.chat.id, "Выбери режим:", reply_markup=get_mode_inline_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def callback_mode(call):
    if call.data == "mode_email":
        user_mode[call.from_user.id] = 'email'
        bot.answer_callback_query(call.id, "Режим: почты")
    else:
        user_mode[call.from_user.id] = 'ip'
        bot.answer_callback_query(call.id, "Режим: IP")

@bot.message_handler(func=lambda m: m.text in ["📧 Чекер почты", "🌐 Чекер IP", "🔄 Сменить режим"])
def handle_buttons(message):
    if message.text == "📧 Чекер почты":
        user_mode[message.from_user.id] = 'email'
        bot.reply_to(message, "Режим: почты")
    elif message.text == "🌐 Чекер IP":
        user_mode[message.from_user.id] = 'ip'
        bot.reply_to(message, "Режим: IP")
    else:
        user_mode[message.from_user.id] = None
        bot.reply_to(message, "Выбери режим")

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    text = message.text.strip()

    # IP
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
    if ips:
        reply = ""
        for ip in ips:
            result, error = check_ip_fraud(ip)
            reply += f"{ip} → {result or error}\n"
        bot.reply_to(message, reply)
        return

    # EMAIL
    emails = extract_emails(text)
    if emails:
        reply = ""
        for email in emails:
            result = check_email(email)
            reply += f"{email} → {'✅' if result else '❌'}\n"
        bot.reply_to(message, reply)
        return

    bot.reply_to(message, "Не нашёл данных")

# ────────────────────────────────────────────────

print("🤖 Бот запущен")
bot.polling(none_stop=True)