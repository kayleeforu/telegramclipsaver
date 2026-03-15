import telegram.ext
import logging
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters
import os
from inlineProcessing import processInline
from linkProcessing import processLink
from instagramPost import processInstagramPost

logging.basicConfig(
   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
   level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="This is a test message.\n\n" \
        "Hello, how are you, " + str(update.effective_user.first_name) + "?"
        )

patternsVideos = [
    r"(https://)?v.\.tiktok\.com/.*/",
    r"(https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?.*",
    r"(https://(www\.)?)?tiktok.com/.*/",
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

    startHandler = CommandHandler('start', start)
    application.add_handler(startHandler)

    videoLinkHandler = telegram.ext.MessageHandler((filters.TEXT & filters.Regex(combinedVideos)), processLink, False)
    inlineVideoLinkHandler = telegram.ext.InlineQueryHandler(processInline, pattern=combinedVideos)
    application.add_handler(inlineVideoLinkHandler)
    application.add_handler(videoLinkHandler)

    photoLinkHandler = telegram.ext.MessageHandler((filters.TEXT & filters.Regex(r"(https://(www\.))?instagram\.com/p/(.{11})/.*")), processInstagramPost)

    application.run_polling()