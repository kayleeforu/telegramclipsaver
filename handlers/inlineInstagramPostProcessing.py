import os
from glob import glob
from telegram import Update, InputMediaPhoto, InputMediaVideo, InlineQueryResultCachedVideo, InlineQueryResultCachedMpeg4Gif
from telegram.ext import ContextTypes
from gallery_dl import config, job
import uuid
import db

# Initialize database
database = db.database()
proxy = os.environ.get("INSTAGRAM_PROXY")

# Configure gallery-dl
config.load()
config.set(("extractor",), "cookies", "cookies.txt")
if proxy:
    config.set(("extractor",), "proxy", proxy)

# Folder cleanup function
def clear_gallery_dl_folder():
    for file in glob("gallery-dl/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

# Main function to process Instagram posts inline
async def inlineInstagramPostProcessing(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str):
    # Clear previous downloads
    clear_gallery_dl_folder()

    # Try downloading the Instagram post
    try:
        config.load()
        config.set(("extractor",), "cookies", "cookies.txt")
        if proxy:
            config.set(("extractor",), "proxy", proxy)
        job.DownloadJob(link).run()
    except Exception as e:
        print(f"Instagram error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Instagram link.")
        return False

    # Prepare media for sending
    media = []
    for file in sorted(glob("gallery-dl/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith((".jpg", ".jpeg", ".webp", ".png")):
            media.append(InputMediaPhoto(open(file, "rb")))

    if not media:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Could not download the Instagram post.")
        clear_gallery_dl_folder()
        return False

    # Send media to your channel
    msg = await context.bot.send_media_group(chat_id=-1003794009076, media=media)

    # Collect file IDs for database
    files = []
    for entry in msg:
        if entry.video:
            files.append((entry.video.file_id, True))
        else:
            files.append((entry.photo[-1].file_id, False))

    # Clean up downloaded files
    clear_gallery_dl_folder()

    # Insert into database
    await database.insert(link, files)

    # Optionally, prepare inline query results
    inline_results = []
    for file_id, has_audio in files:
        if has_audio:
            inline_results.append(
                InlineQueryResultCachedVideo(
                    id=str(uuid.uuid4()),
                    video_file_id=file_id,
                    title="Video"
                )
            )
        else:
            inline_results.append(
                InlineQueryResultCachedMpeg4Gif(
                    id=str(uuid.uuid4()),
                    mpeg4_file_id=file_id,
                    title="GIF"
                )
            )

    # Answer inline query
    if update.inline_query:
        await context.bot.answer_inline_query(
            inline_query_id=update.inline_query.id,
            results=inline_results
        )

    return True