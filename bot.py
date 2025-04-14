from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import logging
import os
from dotenv import load_dotenv
import requests
import json

# --- Загрузка переменных окружения и настройки (как в вашем коде) ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MODEL_NAME = "gemini-1.5-flash-latest"
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Функция для вызова Gemini API (как в вашем коде) ---
def get_gemini_response(query: str):
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY не доступен внутри функции get_gemini_response.")
        return {"error": "API ключ Gemini не настроен."}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}'
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": query}]}]}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Ошибка при запросе к Gemini API: {e}"
        try:
            if e.response is not None:
                error_details = e.response.json()
                error_message += f"\nДетали от API: {json.dumps(error_details, indent=2, ensure_ascii=False)}"
                error_message += f"\nТекст ответа сервера: {e.response.text}"
        except (ValueError, AttributeError):
            if hasattr(e, 'response') and e.response is not None:
                error_message += f"\nТекст ответа сервера: {e.response.text}"
        logger.error(error_message)
        return {"error": error_message}
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при запросе к Gemini API: {e}")
        return {"error": f"Непредвиденная ошибка: {e}"}

# --- Глобальный словарь для хранения контекста диалога ---
user_context = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_context[chat_id] = {} # Инициализация контекста для нового пользователя
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n\nЯ готов помочь вам с выбором услуг автомойки. Задайте свой вопрос."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Просто напишите мне свой вопрос об услугах автомойки.\n\nКоманды:\n/start - Начать диалог\n/help - Показать это сообщение"
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_query = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id

    logger.info(f"Сообщение от {user.username} ({user.id}) в чате {chat_id}: '{user_query[:50]}...'")
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    if chat_id not in user_context:
        user_context[chat_id] = {}

    current_context = user_context[chat_id].get('context', "")
    prompt = f"Ты - консультант по обслуживанию автомоек. Учитывай предыдущий диалог:\n\n{current_context}\n\nОтветь на следующий вопрос пользователя и, если необходимо, задай уточняющий вопрос, чтобы помочь ему выбрать подходящую услугу:\n\n{user_query}"

    response = get_gemini_response(prompt)

    if "error" in response:
        logger.error(f"Ошибка Gemini API для {user.username}: {response['error']}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    else:
        try:
            generated_text = response['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Ответ Gemini для {user.username}: '{generated_text[:50]}...'")
            await update.message.reply_text(generated_text)
            # Обновляем контекст, добавляя как запрос пользователя, так и ответ бота
            user_context[chat_id]['context'] = f"{current_context}\nКлиент: {user_query}\nБот: {generated_text}"

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Ошибка разбора ответа Gemini для {user.username}: {e}. Полный ответ: {response}")
            await update.message.reply_text("Некорректный ответ от Gemini.")

def main() -> None:
    logger.info("Запуск бота...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    logger.info("Бот запущен и готов принимать сообщения.")
    application.run_polling()
    logger.info("Бот остановлен.")

if __name__ == '__main__':
    main()