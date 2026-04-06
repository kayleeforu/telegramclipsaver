from telegram import Update
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
from handlers.photosProcessing import processTikTokSlideshow
from utilities.cacheVideo import uploadToChannel
import subprocess
import asyncio
import db
import logging

clearVids = "rm -f downloadedVideos/*"
database = db.database()

async def processLink(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    isTiktok = "tiktok" in link

    def runDownload():
        return downloadVideo(link)

    loop = asyncio.get_event_loop()
    filepath, hasAudio, audioPath, thumbnailpath, height, width = await loop.run_in_executor(None, runDownload)

    if filepath is None:
        subprocess.run(clearVids, shell=True)
        if isTiktok:
            result = await processTikTokSlideshow(context, link)
            return "slideshow" if result else False
        else:
            return False
    elif filepath == "too_long":
        subprocess.run(clearVids, shell=True)
        return False

    try:
        file = await uploadToChannel(context, filepath, hasAudio, audioPath, thumbnailpath, height, width, link)
        if file is None:
            logging.error("[processLink] Failed to upload file via uploadToChannel")
            return False
    except Exception as e:
        logging.error(f"[processLink] Error sending video: {e}")
        return False
    finally:
        subprocess.run(clearVids, shell=True)
        await database.removeLink(link)

    await database.insert(link, file)
    return True