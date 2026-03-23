from telegram import Update
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
import subprocess
import db
import os

clearVids = ["rm", "-f", "downloadedVideos/*"]
database = db.database()

async def processLink(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    (filepath, hasAudio, thumbnailpath, height, width) = await downloadVideo(link)

    if filepath is None:
        subprocess.run(clearVids)
        return False
    elif filepath == "too_long":
        # Send a message that the video is too long
        subprocess.run(clearVids)
        return False
    ### TODO Too long situation
    
    # Filepath is Not None
    try:
        with open (filepath, "rb") as f:
            if hasAudio:
                msg = await context.bot.send_video(
                    chat_id = -1003794009076,
                    video = f,
                    supports_streaming = True,
                    thumbnail = thumbnailpath,
                    height = height,
                    width = width
                )
                file = (msg.video.file_id, True)
            else:
                msg = await context.bot.send_animation(
                    chat_id = -1003794009076,
                    animation = f,
                    thumbnail = thumbnailpath,
                    height = height,
                    width = width
                )
                file = (msg.animation.file_id, False)
        try:
            os.remove(filepath)
            os.remove(thumbnailpath)
        except:
             print(f"{filepath} or {thumbnailpath} doesn't exist")
    finally:
        subprocess.run(clearVids) # Clear downloadedVideos Folder
    
    await database.insert(link, file) # Insert the data in cache

    return True