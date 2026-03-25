from gallery_dl import config, job
import os
from glob import glob
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db

database = db.database()
proxy = os.environ.get("INSTAGRAM_PROXY")

config.load()
config.set(("extractor",), "cookies", "cookies.txt")
if proxy:
    config.set(("extractor",), "proxy", proxy)

def clear_gallery_dl_folder():
    for file in glob("gallery-dl/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

async def processInstagramPost(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    clear_gallery_dl_folder()

    try:
        config.load()
        config.set(("extractor",), "cookies", "cookies.txt")
        if proxy:
            config.set(("extractor",), "proxy", proxy)
        job.DownloadJob(link).run()
    except Exception as e:
        print(f"Instagram error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Link.")
        return False

    media = []
    for file in sorted(glob("gallery-dl/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith((".jpg", ".jpeg", ".webp", ".png")):
            media.append(InputMediaPhoto(open(file, "rb")))

    if not media:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Could not download post.")
        return False

    msg = await context.bot.send_media_group(chat_id=-1003794009076, media=media)

    files = []
    for entry in msg:
        if entry.video:
            files.append((entry.video.file_id, True))
        else:
            files.append((entry.photo[-1].file_id, False))

    for file in glob("gallery-dl/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

    await database.insert(link, files)
    return True