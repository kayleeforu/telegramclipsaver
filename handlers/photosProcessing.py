from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, LoginRequired
from gallery_dl import config, job
import os
import asyncio
from glob import glob
from telegram import InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import logging
import db

database = db.database()
proxy = os.environ.get("INSTAGRAM_PROXY")
SLIDESHOW_DIR = "tiktok-slideshow"
INSTAGRAM_DIR = "instagram-downloads"
SESSION_FILE = "session.json"
os.makedirs(SLIDESHOW_DIR, exist_ok=True)
os.makedirs(INSTAGRAM_DIR, exist_ok=True)

cl = Client()

def initInstagram():
    username = os.environ.get("INSTAGRAM_USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD")

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(username, password)
            logging.info("[Instagram] Session loaded successfully")
            return
        except Exception as e:
            logging.warning(f"[Instagram] Session load failed, logging in fresh: {e}")

    cl.login(username, password)
    cl.dump_settings(SESSION_FILE)
    logging.info("[Instagram] Fresh login successful, session saved")

try:
    initInstagram()
except Exception as e:
    logging.error(f"[Instagram] Failed to initialize: {e}")


def clearFolder(directory):
    for file in glob(f"{directory}/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)


async def downloadInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    clearFolder(INSTAGRAM_DIR)

    def download():
        media_pk = cl.media_pk_from_url(link)
        paths = cl.album_download(media_pk, folder=INSTAGRAM_DIR)
        return paths

    try:
        loop = asyncio.get_running_loop()
        paths = await loop.run_in_executor(None, download)
    except LoginRequired:
        logging.error("[Instagram] Session expired — refresh session.json manually")
        await database.removeLink(link)
        return False
    except ChallengeRequired:
        logging.error("[Instagram] Challenge required — manual action needed on the account")
        await database.removeLink(link)
        return False
    except Exception as e:
        logging.error(f"[Instagram] Download error: {e}")
        await database.removeLink(link)
        return False

    media = []
    for path in sorted(paths, key=lambda p: str(p)):
        path = str(path)
        if path.endswith(".mp4"):
            media.append(InputMediaVideo(open(path, "rb"), supports_streaming=True))
        elif path.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media.append(InputMediaPhoto(open(path, "rb")))

    if not media:
        await database.removeLink(link)
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

    clearFolder(INSTAGRAM_DIR)
    await database.insert(link, files)
    return True


async def downloadTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    clearFolder(SLIDESHOW_DIR)
    try:
        config.load()
        config.set(("extractor",), "cookies", "cookies.txt")
        config.set(("extractor",), "base-directory", SLIDESHOW_DIR)
        if proxy:
            config.set(("extractor",), "proxy", proxy)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: job.DownloadJob(link).run())
    except Exception as e:
        logging.error(f"[TikTok] Download error: {e}")
        await database.removeLink(link)
        return False

    media = []
    for file in sorted(glob(f"{SLIDESHOW_DIR}/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media.append(InputMediaPhoto(open(file, "rb")))

    if not media:
        await database.removeLink(link)
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

    clearFolder(SLIDESHOW_DIR)
    await database.insert(link, files)
    return True


async def processTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadTikTokSlideshow(context, link)

async def processInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadInstagramPost(context, link)