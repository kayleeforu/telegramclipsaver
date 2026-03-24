from instaloader import Instaloader, Post
import os
from glob import glob
import re
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db

database = db.database()
instagram_user = os.environ.get("INSTAGRAM_USER")

instance = Instaloader()
session_file = f"sessions/session-{instagram_user}"
if os.path.exists(session_file):
    instance.load_session_from_file(instagram_user, session_file)
else:
    raise RuntimeError("No session file")

async def processInstagramPost(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    for file in glob("downloadedVideos/*"):
        os.remove(file)
    match = re.search(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]{11})", link)
    if not match:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Link.")
        return False
    shortcode = match.group(1)
    try:
        post = Post.from_shortcode(instance.context, shortcode)
    except Exception as e:
        print(f"Instagram error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Link.")
        return False
    instance.download_post(post=post, target="downloadedVideos")
    media = []
    for file in sorted(glob("downloadedVideos/*")):
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith(".jpg"):
            media.append(InputMediaPhoto(open(file, "rb")))
    msg = await context.bot.send_media_group(chat_id=-1003794009076, media=media)
    files = []
    for entry in msg:
        if entry.video:
            files.append((entry.video.file_id, True))
        else:
            files.append((entry.photo[-1].file_id, False))
    for file in glob("downloadedVideos/*"):
        os.remove(file)
    await database.insert(link, files)
    return True