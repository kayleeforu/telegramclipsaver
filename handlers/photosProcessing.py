from gallery_dl import config, job
import os
import asyncio
from glob import glob
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db

database = db.database()
proxy = os.environ.get("INSTAGRAM_PROXY")

SLIDESHOW_DIR = "tiktok-slideshow"
INSTAGRAM_DIR = "instagram-downloads"
os.makedirs(SLIDESHOW_DIR, exist_ok=True)
os.makedirs(INSTAGRAM_DIR, exist_ok=True)

def clearFolder(directory):
    for file in glob(f"{directory}/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

async def downloadMediaGroup(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str, directory: str, errorText: str):
    clearFolder(directory)
    try:
        config.load()
        config.set(("extractor",), "cookies", "cookies.txt")
        config.set(("extractor",), "base-directory", directory)
        if proxy:
            config.set(("extractor",), "proxy", proxy)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: job.DownloadJob(link).run())
    except Exception as e:
        print(f"Download error: {e}")
        await database.removeLink(link)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Link.")
        return False

    media = []
    for file in sorted(glob(f"{directory}/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media.append(InputMediaPhoto(open(file, "rb")))

    if not media:
        await database.removeLink(link)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=errorText)
        return False

    msgs = []
    for i in range(0, len(media), 10):
        chunk = media[i:i+10]
        chunk_msgs = await context.bot.send_media_group(chat_id=-1003794009076, media=chunk)
        msgs.extend(chunk_msgs)
        if i + 10 < len(media):
            await asyncio.sleep(5)

    files = []
    for entry in msgs:
        if entry.video:
            files.append((entry.video.file_id, True))
        else:
            files.append((entry.photo[-1].file_id, False))

    clearFolder(directory)
    await database.insert(link, files)
    return True

async def processTikTokSlideshow(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(update, context, link, SLIDESHOW_DIR, "Could not download slideshow.")

async def processInstagramPost(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(update, context, link, INSTAGRAM_DIR, "Could not download post.")