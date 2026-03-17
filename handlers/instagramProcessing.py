from instaloader import Instaloader, Post
import os
from glob import glob
import subprocess
import re
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db

clearVids = ["rm", "-f", "/home/kaylee/telegramclipsaver/downloadedVideos/*"]
database = db.database()

async def processInstagramPost(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    shortcode = (re.search(r"(https://(www\.))?instagram\.com/p/(.{11})/.*", link)).group(3)

    instance = Instaloader()
    try:
        post = Post.from_shortcode(instance.context, shortcode)
    except:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Invalid Link."
        )
        return False
    
    subprocess.run(clearVids)

    instance.download_post(post = post, target = "downloadedVideos")

    media = []
    for file in glob("downloadedVideos/*"):
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming = True))
        if file.endswith(".jpg"):
            media.append(InputMediaPhoto(open(file, "rb")))
    
    msg = await context.bot.send_media_group(
        chat_id = -1003794009076,
        media = media,
    )

    media2 = []
    files = []
    for entry in msg:
        if entry.video:
            files.append((entry.video.file_id, True))
            media2.append(InputMediaVideo(entry.video.file_id))
        else:
            files.append((entry.photo[-1].file_id, False))
            media2.append(InputMediaPhoto(entry.photo[-1].file_id))

    for file in glob("downloadedVideos/*"):
        os.remove(file)

    await database.insert(link, files)

    return True