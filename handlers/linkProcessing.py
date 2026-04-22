from telegram import Update
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
from handlers.photosProcessing import processTikTokSlideshow
from utilities.cacheVideo import uploadToChannel
import asyncio
import tempfile
import shutil
import db
import logging

database = db.database()


async def processLink(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    isTiktok = "tiktok" in link

    tmp_dir = tempfile.mkdtemp(prefix="video_")
    loop = asyncio.get_event_loop()

    try:
        filepath, hasAudio, audioPath, thumbnailpath, height, width = await loop.run_in_executor(
            None, downloadVideo, link, tmp_dir
        )

        if filepath is None:
            if isTiktok:
                result = await processTikTokSlideshow(context, link)
                return "slideshow" if result else False
            else:
                return False

        elif filepath == "too_long":
            return False

        try:
            file = await uploadToChannel(context, filepath, hasAudio, audioPath, thumbnailpath, height, width)
            if file is None:
                logging.error("[processLink] Failed to upload file via uploadToChannel")
                return False
        except Exception as e:
            logging.error(f"[processLink] Error sending video: {e}")
            return False

        await database.removeLink(link)
        await database.insert(link, file)
        return True

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)