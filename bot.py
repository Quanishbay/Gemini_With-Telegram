import logging
import os
import requests
import re
from openai import OpenAI
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CLIENT_API_URL = os.getenv('CLIENT_API_URL', "http://localhost:8000/api/create-client")
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
API_EMAIL = os.getenv('API_EMAIL')
API_PASSWORD = os.getenv('API_PASSWORD')
CAR_WASH_ID = os.getenv('CAR_WASH_ID')

OPENAI_MODEL = "gpt-4"
client = OpenAI(api_key=OPENAI_API_KEY)

REGISTRATION_KEYWORDS = {
    "зарегистрироваться", "регистрация", "записаться", "запись на мойку",
    "новый клиент", "стать клиентом", "оформить карту", "нужна запись",
}

SERVICE_KEYWORDS = {
    "услуги", "что моете", "какие услуги", "список услуг", "прайс",
    "цены", "стоимость", "сколько стоит", "узнать цены",
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_context = {}
api_access_token = None
cached_services = []

def get_access_token():
    global api_access_token
    if api_access_token:
        return api_access_token
    try:
        response = requests.post(f"{API_BASE_URL}/api/auth/login", json={'email': API_EMAIL, 'password': API_PASSWORD}, timeout=10)
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if access_token:
            api_access_token = access_token
            return access_token
        return None
    except Exception as e:
        logger.error(f"API auth error: {e}")
        return None

def get_services_from_api():
    global cached_services
    token = get_access_token()
    if not token:
        return None
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/car-washes/services-by-id",
            headers={"Authorization": f"Bearer {token}"},
            params={"id": CAR_WASH_ID},
            timeout=10
        )
        response.raise_for_status()
        services_data = response.json()
        if isinstance(services_data, list):
            cached_services = services_data
        elif isinstance(services_data, dict) and 'services' in services_data:
            cached_services = services_data['services']
        else:
            cached_services = []
        return cached_services
    except Exception as e:
        logger.error(f"Error fetching services: {e}")
        cached_services = []
        return None

def get_services_cached():
    if not cached_services:
        return get_services_from_api()
    return cached_services

def get_openai_response(prompt):
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — виртуальный консультант премиум-автомойки 'Чистый Блеск'. "
                        "Твоя задача — отвечать кратко, профессионально и с заботой о клиенте. "
                        "Не используй шаблонные фразы, не перенаправляй к администратору и не извиняйся. "
                        "Отвечай так, будто ты опытный сотрудник. "
                        "Если вопрос не по теме, переориентируй в сторону услуг автомойки. "
                        "Будь лаконичным, но полезным. "
                        "Если клиент спрашивает об услугах — дай чёткий список, если хочет записаться — предложи услугу или направь на запись. "
                        "Твоя цель — быстро помочь клиенту и убедить, что у нас — лучший сервис."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Произошла ошибка при обращении к ИИ. Пожалуйста, попробуйте позже."

def validate_and_clean_phone_number(phone):
    cleaned = re.sub(r'\D', '', phone)
    return f"+{cleaned}" if phone.strip().startswith('+') and len(cleaned) >= 7 else cleaned if len(cleaned) >= 7 else None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_context[chat_id] = {}
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Привет, {user_name}! Я консультант автомойки 'Чистый Блеск'. Напишите, если хотите узнать об услугах или записаться.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - начать\n/register - записаться\n/help - помощь")

async def register_client_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_context[chat_id] = {'step': 'awaiting_name'}
    await update.message.reply_text("Введите ваше имя:")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    step = user_context.get(chat_id, {}).get('step')

    if step == 'awaiting_name':
        user_context[chat_id]['name'] = text
        user_context[chat_id]['step'] = 'awaiting_phone'
        await update.message.reply_text("Теперь введите номер телефона:")
        return

    if step == 'awaiting_phone':
        phone = validate_and_clean_phone_number(text)
        if not phone:
            await update.message.reply_text("Неверный формат номера. Повторите ввод:")
            return
        user_context[chat_id]['phone'] = phone
        services = get_services_cached()
        user_context[chat_id]['step'] = 'awaiting_service'
        service_list = '\n'.join([
            f"{i+1}. {s.get('service_name', 'Без названия')} - {s.get('price', 'цена неизвестна')}"
            for i, s in enumerate(services)
        ])
        await update.message.reply_text(f"Выберите услугу, введя номер из списка:\n{service_list}")
        return

    if step == 'awaiting_service':
        services = get_services_cached()
        try:
            selected_index = int(text.strip()) - 1
            if selected_index < 0 or selected_index >= len(services):
                await update.message.reply_text("Неверный номер. Повторите ввод, выбрав номер из списка.")
                return
            service = services[selected_index]
            service_id = service.get("id")
            if not service_id:
                logger.error(f"Ошибка: услуга без ID: {service}")
                await update.message.reply_text("Ошибка: выбранная услуга не содержит ID. Пожалуйста, выберите другую или попробуйте позже.")
                return
            data = {
                "name": user_context[chat_id]['name'],
                "phone": user_context[chat_id]['phone'],
                "service_id": service_id
            }
            logger.info(f"Отправка данных на API: {data}")
            response = requests.post(CLIENT_API_URL, json=data, timeout=10)
            if response.status_code in [200, 201]:
                await update.message.reply_text(f"Запись на '{service['service_name']}' прошла успешно!")
            else:
                logger.error(f"Ответ от API {response.status_code}: {response.text}")
                await update.message.reply_text("Ошибка при записи. Попробуйте позже.")
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректный номер из списка.")
        except Exception as e:
            logger.error(f"Ошибка при выборе услуги: {e}")
            await update.message.reply_text("Произошла ошибка. Повторите ввод номера услуги.")
        user_context[chat_id] = {}
        return

    if any(k in text.lower() for k in REGISTRATION_KEYWORDS):
        await register_client_command(update, context)
        return

    if any(k in text.lower() for k in SERVICE_KEYWORDS):
        services = get_services_cached()
        service_list = '\n'.join([
            f"{i+1}. {s['service_name']} - {s.get('price', 'цена неизвестна')}"
            for i, s in enumerate(services)
        ])
        await update.message.reply_text(f"Наши услуги:\n{service_list}")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    prompt = f"Ты — консультант автомойки. Клиент спрашивает: {text}"
    reply = get_openai_response(prompt)
    await update.message.reply_text(reply)

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN not set")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register_client_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
