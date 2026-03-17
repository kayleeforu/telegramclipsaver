import logging
from telegram.ext import ApplicationBuilder, CommandHandler, filters, MessageHandler, InlineQueryHandler
import os
from handlers.inlineProcessing import processInline
from handlers.linkProcessing import processLink
from handlers.instagramProcessing import processInstagramPost
from handlers.otherMessageHandling import otherMessage
from commands.commands import start, support

logging.basicConfig(
   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
   level=logging.INFO
)

patternsVideos = [
    r"(https://)?v.\.tiktok\.com/.*",
    r"(https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?.*",
    r"(https://(www\.)?)?tiktok.com/.*",
    r"(https://(www\.)?)?youtube\.com/watch(.*)",
    r"(https://(www\.)?)?youtu\.be/.*",
    r"(https://(www\.)?)?youtube\.com/shorts/.*",
    r"(https://(www\.)?)?instagram\.com/reel/.*",
    r"(https://(www\.)?)?pin\..{2}/.*",
    r"(https://(www\.)?)?pinterest\.com/pin/.*",
]

combinedVideos = "|".join(f"({p})" for p in patternsVideos)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")

    application = ApplicationBuilder() \
    .token(TOKEN) \
    .base_url("http://localhost:8081/bot") \
    .base_file_url("http://localhost:8081/file/bot") \
    .concurrent_updates(True)\
    .read_timeout(120) \
    .write_timeout(120) \
    .connect_timeout(120) \
    .build()

    # Commands
    startHandler = CommandHandler("start", start)
    supportHandler = CommandHandler("support", support)
    application.add_handlers([startHandler, supportHandler])

    # Link, which is not instagram post, handler
    videoLinkHandler = MessageHandler((filters.TEXT & filters.Regex(combinedVideos)), processLink, False)
    inlineVideoLinkHandler = InlineQueryHandler(processInline, pattern=combinedVideos, block = True)
    application.add_handlers([inlineVideoLinkHandler, videoLinkHandler])

    # Instagram post download
    instagramPostLinkHandler = MessageHandler((filters.TEXT & filters.Regex(r"(https://(www\.))?instagram\.com/p/(.{11})/.*")), processInstagramPost)
    application.add_handler(instagramPostLinkHandler)

    # If user sends any other message than the supported link or command
    anyMessageHandler = MessageHandler(filters.TEXT, otherMessage)
    application.add_handler(anyMessageHandler)
    
    # Run bot
    application.run_polling()