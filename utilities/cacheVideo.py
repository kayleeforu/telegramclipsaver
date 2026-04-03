from telegram import Update
from telegram.ext import ContextTypes
import logging
import subprocess
import db

clearVids = "rm -f downloadedVideos/*"
database = db.database()

async def uploadToChannel(context: ContextTypes.DEFAULT_TYPE, filepath, hasAudio, thumbnailpath, height, width, link):
    try:
        with open(filepath, "rb") as file:
            if "instagram" in link:
                hasAudio = True
            if hasAudio:
                message = await context.bot.send_video(
                    chat_id = -1003794009076,
                    video = file,
                    supports_streaming = True,
                    thumbnail = thumbnailpath,
                    height = height,
                    width = width
                )
                if message.video:
                    return (message.video.file_id, True)
                elif message.document:
                    return (message.document.file_id, True)
                else:
                    return None
            elif not hasAudio:
                message = await context.bot.send_animation(
                    chat_id = -1003794009076,
                    animation = file,
                    thumbnail=thumbnailpath,
                    height=height,
                    width=width
                )
                if message.animation:
                    return (message.animation.file_id, False)
                elif message.document:
                    return (message.document.file_id, False)
                else:
                    return None
    except:
        logging.error("File was not found. Inline Query Error")
        return None
    finally:
        subprocess.run(clearVids, shell=True)