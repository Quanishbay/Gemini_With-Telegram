import os

from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from app.handlers.conversation_handler import start, get_name, get_service, get_wash

def main():
    application = Application.builder().token("7896573414:AAGZUeOK3Ypy14gh0L_IfI-BxJD67okQ3M8").build()

    NAME, SERVICE_SELECTION, WASH_SELECTION = range(3)


    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SERVICE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            WASH_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_wash)],
        },
        fallbacks=[],
    )

    application.add_handler(conversation_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
