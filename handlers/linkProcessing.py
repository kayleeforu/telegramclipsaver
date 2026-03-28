from telegram import Update
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
import subprocess
import db
import logging

clearVids = "rm -f downloadedVideos/*"
database = db.database()

async def processLink(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    (filepath, hasAudio, thumbnailpath, height, width) = await downloadVideo(link)
    
    if filepath is None:
        subprocess.run(clearVids, shell=True)
        return False
    elif filepath == "too_long":
        subprocess.run(clearVids, shell=True)
        return False

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
                file = (msg.video.file_id, True)
            else:
                msg = await context.bot.send_animation(
                    chat_id=-1003794009076,
                    animation=f,
                    thumbnail=thumbnailpath,
                    height=height,
                    width=width
                )
                file = (msg.animation.file_id, False)
    except Exception as e:
        logging.error(f"[processLink] Error sending video: {e}")
        return False
    finally:
        subprocess.run(clearVids, shell=True)

    await database.insert(link, file)
    return True