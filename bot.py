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

    filepath = downloadVideo(link)
    if filepath is None:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Invalid URL.\nTry an existing URL."
        )
    with open(filepath, "rb") as f:
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=f,
            caption = "Here is your video.\n@clip_saverbot"
        )

patterns = [
    r"^(https://)?v.\.tiktok\.com/.{9}/$",
    r"^(https://(www\.)?)?tiktok\.com/@.*/\d{19}(\?.*)\?$",
    r"^(https://(www\.)?)?youtube\.com/watch\?v=.{11}$",
    r"(^(https://(www\.)?)?youtu\.be/.{11}$)",
]

combined = "|".join(f"({p})" for p in patterns)

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")

    application = ApplicationBuilder().token(TOKEN).local_mode(False).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    link_handler = telegram.ext.MessageHandler((filters.TEXT & filters.Regex(combined)), video, True)
    application.add_handler(link_handler)

    application.run_polling()
