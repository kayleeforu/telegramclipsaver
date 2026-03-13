import telegram.ext
import logging
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters
from savevid import downloadVideo
import os

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

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    requestedBy = "@".join(update.effective_sender.username) if isGroupChat else None
    requestedMessage = update.effective_message.id if isGroupChat else None

    filepath = downloadVideo(link)
    if filepath is None:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Invalid URL.\nTry an existing URL."
        )
        return
    
    try:
        with open(filepath, "rb") as f:
            caption = f"Here is your video.\nRequested by: {requestedBy}\n\n@clip_saverbot"if isGroupChat \
                else "Here is your video.\n\n@clip_saverbot"
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=f,
                caption=caption,
                supports_streaming=True
            )
            if requestedBy is not None:
                await context.bot.delete_message(update.effective_chat.id, requestedMessage)
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    with open("downloadedCount.txt", "r+") as f:
        count = int(f.read())
        print(count)
        count += 1
        f.seek(0)
        f.write(str(count))

patterns = [
    r"(https://)?v.\.tiktok\.com/.{9}/",
    r"(https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?.*",
    r"(https://(www\.)?)?youtube\.com/watch(.*)",
    r"(https://(www\.)?)?youtu\.be/.*",
    r"(https://(www\.)?)?youtube\.com/shorts/.*",
    r"(https://(www\.)?)?instagram\.com/reel/.*",
    r"(https://(www\.)?)?pin\..{2}/.*",
    r"(https://(www\.)?)?pinterest\.com/pin/.*",
]

combined = "|".join(f"({p})" for p in patterns)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")

    application = ApplicationBuilder() \
    .token(TOKEN) \
    .base_url("http://localhost:8081/bot") \
    .base_file_url("http://localhost:8081/file/bot") \
    .build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    link_handler = telegram.ext.MessageHandler((filters.TEXT & filters.Regex(combined)), video, False)
    application.add_handler(link_handler)

    application.run_polling()