import logging
from telegram.ext import ApplicationBuilder, CommandHandler, filters, MessageHandler, InlineQueryHandler, ChosenInlineResultHandler
from telegram import Update
import os
from handlers.inlinePostProcessing import processPostInline, chosenInlineResult
from handlers.linkAnswer import processMessage
from commands.commands import start, support

logging.basicConfig(
   format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
   level = logging.INFO
)

videoPost = [
    r"((https://)?v.\.tiktok\.com/\S*)",
    r"((https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?\S*)",
    r"((https://(www\.)?)?tiktok.com/\S*)",
    r"((https://(www\.)?)?youtube\.com/watch(\S*))",
    r"((https://(www\.)?)?youtu\.be/\S*)",
    r"((https://(www\.)?)?youtube\.com/shorts/\S*)",
    r"((https://(www\.)?)?pin\..{2}/\S*)",
    r"((https://(www\.)?)?pinterest\.com/pin/\S*)",
]
combinedVideos = "|".join(f"({p})" for p in videoPost)

instagramPost = r"((https://(www\.))?instagram\.com/p/(.*)/\S*)|((https://(www\.)?)?instagram\.com/reel/\S*)"

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    BOT_API_URL = os.getenv("BOT_API_URL", "http://telegram-bot-api:8081/bot")
    BOT_API_FILE_URL = os.getenv("BOT_API_FILE_URL", "http://telegram-bot-api:8081/file/bot")

    application = ApplicationBuilder() \
        .token(TOKEN) \
        .base_url(BOT_API_URL) \
        .base_file_url(BOT_API_FILE_URL) \
        .concurrent_updates(True) \
        .read_timeout(120) \
        .write_timeout(120) \
        .connect_timeout(120) \
        .build()

    # Handlers
    startHandler = CommandHandler("start", start)
    supportHandler = CommandHandler("support", support)
    messageHandler = MessageHandler(filters.TEXT & (~filters.COMMAND), processMessage)
    
    # Inline Handlers
    inlineVideoLinkHandler = InlineQueryHandler(processPostInline, pattern = combinedVideos)
    inlineInstagramPostLinkHandler = InlineQueryHandler(processPostInline, pattern = instagramPost)
    chosenInlineResultHandler = ChosenInlineResultHandler(chosenInlineResult)

    # Adding handlers
    application.add_handler(startHandler)
    application.add_handler(supportHandler)
    application.add_handler(inlineVideoLinkHandler)
    application.add_handler(inlineInstagramPostLinkHandler)
    application.add_handler(chosenInlineResultHandler)
    application.add_handler(messageHandler)

    # Run bot
    application.run_polling(allowed_updates = Update.ALL_TYPES)