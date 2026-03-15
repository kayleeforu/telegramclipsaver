from instaloader import Instaloader, Post
import os
from glob import glob
import re
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from count import countAdd
from deleteOriginalMessage import deleteOriginalMessage

async def processInstagramPost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    match = re.search(r"(https://(www\.))?instagram\.com/p/(.{11})/.*", link)
    if match:
        shortcode = match.group(3)
    
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    requestedBy = "@" + update.effective_sender.username if isGroupChat else None
    requestedMessage = update.effective_message.id if isGroupChat else None

    caption = f"Here is your post.\nRequested by: {requestedBy}\n\n@clip_saverbot"if isGroupChat \
                else "Here is your post.\n\n@clip_saverbot"

    instance = Instaloader()
    
    try:
        post = Post.from_shortcode(instance.context, shortcode)
    except:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Invalid Link."
        )
        return
    
    for file in glob("downloadedVideos/*"):
        os.remove(file)

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
    for entry in msg:
        if entry.video:
            media2.append(InputMediaVideo(entry.video.file_id))
        else:
            media2.append(InputMediaPhoto(entry.photo[-1].file_id))
    media2[-1].caption = caption

    for file in glob("downloadedVideos/*"):
        os.remove(file)

    await context.bot.send_media_group(
        chat_id = update.effective_chat.id,
        media = media2
    )

    countAdd()

    await deleteOriginalMessage(update, context, requestedMessage, requestedBy)

    return