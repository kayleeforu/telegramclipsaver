from telegram import Update
from telegram.ext import ContextTypes
from savevid import downloadVideo
from count import countAdd
import subprocess
import db
from deleteOriginalMessage import deleteOriginalMessage
import os

clearVids = ["rm", "-f", "/home/kaylee/telegramclipsaver/downloadedVideos/*"]
database = db.database()

async def processLink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    requestedBy = "@" + update.effective_sender.username if isGroupChat else None
    requestedMessage = update.effective_message.id if isGroupChat else None

    caption = f"Here is your video.\nRequested by: {requestedBy}\n\n@clip_saverbot"if isGroupChat \
                else "Here is your video.\n\n@clip_saverbot"

    # Cache check
    response = await database.lookup(link)
    if response.data:
        row = response.data[0]
        file = (row["file_ids"][0], row["has_audio"][0])
        if file[1]:
                await context.bot.send_video(
                    chat_id = update.effective_chat.id,
                    video = file[0],
                    caption = caption
                )
        else:
                await context.bot.send_animation(
                    chat_id = update.effective_chat.id, 
                    animation = file[0],
                    caption = caption
                )
        await countAdd() # Downloaded Count + 1

        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
    
        return

    (filepath, hasAudio, thumbnailpath, height, width) = await downloadVideo(link)

    # Cache Has No Entry, filepath check
    if filepath is None:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Unknown issue."
        )
        subprocess.run(clearVids) # Clear downloadedVideos Folder
        return
    elif filepath == "too_long":
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "The video is too long.\nTry a video that is shorter than 10 minutes."
        )
        subprocess.run(clearVids) # Clear downloadedVideos Folder
        return
    
    # Filepath is Not None, sending the video
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

                await context.bot.send_video(
                     chat_id = update.effective_chat.id,
                     video = file[0],
                     supports_streaming = True,
                     caption = caption
                )
            else:
                msg = await context.bot.send_animation(
                    chat_id = -1003794009076,
                    animation = f,
                    thumbnail = thumbnailpath,
                    height = height,
                    width = width
                )
                file = (msg.animation.file_id, False)

                await context.bot.send_animation(
                     chat_id = update.effective_chat.id,
                     animation = file[0],
                     caption = caption
                )
        try:
            os.remove(filepath)
            os.remove(thumbnailpath)
        except:
             print(f"{filepath} or {thumbnailpath} doesn't exist")
        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)

    finally:
        subprocess.run(clearVids) # Clear downloadedVideos Folder
    
    await database.insert(link, file) # Insert the data in cache

    await countAdd()