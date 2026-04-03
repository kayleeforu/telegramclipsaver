from telegram import Update
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
from handlers.photosProcessing import processTikTokSlideshow
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
    (filepath, hasAudio, thumbnailpath, height, width) = await loop.run_in_executor(None, runDownload)

    if filepath is None:
        subprocess.run(clearVids, shell=True)
        if isTiktok:
            result = await processTikTokSlideshow(context, link)
            return "slideshow" if result else False
        else:
            return False
    elif filepath == "too_long":
        return False
    elif filepath == "too_long_rr":
        with open(thumbnailpath, "rb") as thmb:
            await context.bot.send_video(
                chat_id = update.effective_chat.id,
                height = height,
                width = width,
                video = "BAACAgQAAyEGAATiI_v0AAIE-GnPCL_LfpmGiSYeRlCEwOagV-SvAALqGgACKtx5UgOyaDA3mOiuOgQ",
                thumbnail = thmb,
                caption = "🎬 Downloaded via @clip_saverbot"
            )
        subprocess.run(clearVids, shell=True)
        return None

    try:
        with open(filepath, "rb") as f:
            if hasAudio:
                msg = await context.bot.send_video(
                    chat_id=-1003794009076,
                    video=f,
                    supports_streaming=True,
                    thumbnail=thumbnailpath,
                    height=height,
                    width=width
                )
                if msg.video:
                    file = (msg.video.file_id, True)
                elif msg.document:
                    file = (msg.document.file_id, True)
                else:
                    logging.error("[processLink] Telegram returned message with no video/document")
                    return False
            else:
                msg = await context.bot.send_animation(
                    chat_id=-1003794009076,
                    animation=f,
                    thumbnail=thumbnailpath,
                    height=height,
                    width=width
                )
                if msg.animation:
                    file = (msg.animation.file_id, False)
                elif msg.document:
                    file = (msg.document.file_id, False)
                else:
                    logging.error("[processLink] Telegram returned message with no animation/document")
                    return False
    except Exception as e:
        logging.error(f"[processLink] Error sending video: {e}")
        return False
    finally:
        subprocess.run(clearVids, shell=True)
        await database.removeLink(link)

    await database.insert(link, file)
    return True