from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import Update

from app.services.car_wash_api import get_categories, get_services, get_washes
from app.services.gemini_api import generate_response

NAME, SERVICE_SELECTION, WASH_SELECTION = range(3)


async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Привет! Как тебя зовут?")
    return NAME


async def get_name(update: Update, context: CallbackContext) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "Отлично, а теперь выбери категорию: Внешняя мойка, Внутренняя уборка или Полная химчистка.")
    categories = get_categories()  # Запрашиваем категории
    category_names = [category["name"] for category in categories]
    await update.message.reply_text(f"Категории: {', '.join(category_names)}")
    return SERVICE_SELECTION


async def get_service(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    services = get_services()  # Запрашиваем доступные сервисы
    matching_services = [service for service in services if user_input.lower() in service["name"].lower()]

    if matching_services:
        service_names = [service["name"] for service in matching_services]
        await update.message.reply_text(f"Выберите автомойку из следующих: {', '.join(service_names)}")
        return WASH_SELECTION
    else:
        await update.message.reply_text("Извините, я не нашёл подходящих сервисов. Попробуйте снова.")
        return SERVICE_SELECTION


async def get_wash(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    washes = get_washes()  # Запрашиваем автомойки
    matching_washes = [wash for wash in washes if user_input.lower() in wash["name"].lower()]

    if matching_washes:
        await update.message.reply_text(f"Вы выбрали автомойку {matching_washes[0]['name']}. Приятного обслуживания!")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Не удалось найти автомойку с таким названием. Попробуйте снова.")
        return WASH_SELECTION
