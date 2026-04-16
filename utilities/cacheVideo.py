from telegram import Update
from telegram.ext import ContextTypes
import logging
import db
import time

clearVids = "rm -f downloadedVideos/*"
database = db.database()

async def uploadToChannel(context: ContextTypes.DEFAULT_TYPE, filepath, hasAudio, audioPath, thumbnailpath, height, width):
    try:
        with open(filepath, "rb") as file:
            if hasAudio and audioPath:
                messageAudio = await context.bot.send_audio(
                    chat_id = -1003794009076,
                    audio = audioPath,
                    title = "Audio"
                )
                time.sleep(1)
                message = await context.bot.send_video(
                    chat_id = -1003794009076,
                    video = file,
                    supports_streaming = True,
                    thumbnail = thumbnailpath,
                    height = height,
                    width = width
                )
                audio_file_id = messageAudio.audio.file_id if messageAudio and messageAudio.audio else None
                if message.video:
                    return (message.video.file_id, True, audio_file_id)
                elif message.document:
                    return (message.document.file_id, True, audio_file_id)
                else:
                    return None
            elif not hasAudio:
                message = await context.bot.send_animation(
                    chat_id = -1003794009076,
                    animation = file,
                    thumbnail = thumbnailpath,
                    height = height,
                    width = width
                )
                if message.animation:
                    return (message.animation.file_id, False, None)
                elif message.document:
                    return (message.document.file_id, False, None)
                else:
                    return None

    except Exception as e:
        logging.error(f"uploadToChannel error: {e}")
        return None