from gallery_dl import config, job
import os
import asyncio
from glob import glob
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db

database = db.database()

proxy = os.environ.get("INSTAGRAM_PROXY")
INSTAGRAM_DIR = "instagram-downloads"
os.makedirs(INSTAGRAM_DIR, exist_ok=True)

def clear_instagram_folder():
    for file in glob(f"{INSTAGRAM_DIR}/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

async def processInstagramPost(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str):
    clear_instagram_folder()

    try:
        config.load()
        config.set(("extractor",), "cookies", "cookies.txt")
        config.set(("extractor",), "base-directory", INSTAGRAM_DIR)
        if proxy:
            config.set(("extractor",), "proxy", proxy)

        job.DownloadJob(link).run()

    except Exception as e:
        print(f"Instagram error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid Link."
        )
        return False

    media = []
    for file in sorted(glob(f"{INSTAGRAM_DIR}/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue

        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media.append(InputMediaPhoto(open(file, "rb")))

    if not media:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Could not download post."
        )
        return False

    msgs = []
    for i in range(0, len(media), 10):
        chunk = media[i:i+10]
        chunk_msgs = await context.bot.send_media_group(
            chat_id=-1003794009076,
            media=chunk
        )
        msgs.extend(chunk_msgs)

        if i + 10 < len(media):
            await asyncio.sleep(5)

    files = []
    for entry in msgs:
        if entry.video:
            files.append((entry.video.file_id, True))
        else:
            files.append((entry.photo[-1].file_id, False))

    clear_instagram_folder()
    await database.insert(link, files)

    return True