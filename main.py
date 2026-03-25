import logging
from telegram.ext import ApplicationBuilder, CommandHandler, filters, MessageHandler, InlineQueryHandler
import os
from handlers.inlineVideoProcessing import processInline
from handlers.inlineInstagramPostProcessing import inlineInstagramPostProcessing
from handlers.linkAnswer import processMessage
from commands.commands import start, support

logging.basicConfig(
   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
   level=logging.INFO
)

videoPost = [
    r"((https://)?v.\.tiktok\.com/\S*)",
    r"((https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?\S*)",
    r"((https://(www\.)?)?tiktok.com/\S*)",
    r"((https://(www\.)?)?youtube\.com/watch(\S*))",
    r"((https://(www\.)?)?youtu\.be/\S*)",
    r"((https://(www\.)?)?youtube\.com/shorts/\S*)",
    r"((https://(www\.)?)?instagram\.com/reel/\S*)",
    r"((https://(www\.)?)?pin\..{2}/\S*)",
    r"((https://(www\.)?)?pinterest\.com/pin/\S*)",
]
combinedVideos = "|".join(f"({p})" for p in videoPost)

instagramPost = r"((https://(www\.))?instagram\.com/p/(.{11})/\S*)"

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

    # Commands
    startHandler = CommandHandler("start", start)
    supportHandler = CommandHandler("support", support)
    # Message Handler
    messageHandler = MessageHandler(filters.TEXT, processMessage)
    # Link, which is not instagram post, handler
    inlineVideoLinkHandler = InlineQueryHandler(processInline, pattern = combinedVideos, block = True)
    inlineInstagramPostLinkHandler = InlineQueryHandler(inlineInstagramPostProcessing, pattern = instagramPost, block = True)

    # Adding handlers to the bot
    application.add_handlers([startHandler, supportHandler, messageHandler, inlineVideoLinkHandler, inlineInstagramPostLinkHandler])
    
    # Run bot
    application.run_polling()