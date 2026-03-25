import os
from glob import glob
from telegram import Update, InputMediaPhoto, InputMediaVideo, InlineQueryResultCachedVideo, InlineQueryResultCachedMpeg4Gif
from telegram.ext import ContextTypes
from gallery_dl import config, job
import uuid
import db

database = db.database()
proxy = os.environ.get("INSTAGRAM_PROXY")

config.load()
config.set(("extractor",), "cookies", "cookies.txt")
if proxy:
    config.set(("extractor",), "proxy", proxy)

def clear_gallery_dl_folder():
    for file in glob("gallery-dl/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

def build_inline_results(files):
    results = []
    for file_id, has_audio in files:
        if has_audio:
            results.append(InlineQueryResultCachedVideo(
                id=str(uuid.uuid4()),
                video_file_id=file_id,
                title="Video"
            ))
        else:
            results.append(InlineQueryResultCachedMpeg4Gif(
                id=str(uuid.uuid4()),
                mpeg4_file_id=file_id,
                title="GIF"
            ))
    return results

async def processInstagramPostInline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.inline_query.query

    # Проверяем кэш
    response = await database.lookup(link)
    if response.data:
        row = response.data[0]
        files = list(zip(row["file_ids"], row["has_audio"]))
        inline_results = build_inline_results(files)
        await context.bot.answer_inline_query(
            inline_query_id=update.inline_query.id,
            results=inline_results
        )
        return True

    # Скачиваем
    clear_gallery_dl_folder()
    try:
        config.load()
        config.set(("extractor",), "cookies", "cookies.txt")
        if proxy:
            config.set(("extractor",), "proxy", proxy)
        job.DownloadJob(link).run()
    except Exception as e:
        print(f"Instagram error: {e}")
        return False

    media = []
    for file in sorted(glob("gallery-dl/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue
        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
        elif file.endswith((".jpg", ".jpeg", ".webp", ".png")):
            media.append(InputMediaPhoto(open(file, "rb")))

    if not media:
        clear_gallery_dl_folder()
        return False

    msg = await context.bot.send_media_group(chat_id=-1003794009076, media=media)

    files = []
    for entry in msg:
        if entry.video:
            files.append((entry.video.file_id, True))
        else:
            files.append((entry.photo[-1].file_id, False))

    clear_gallery_dl_folder()
    await database.insert(link, files)

    inline_results = build_inline_results(files)
    await context.bot.answer_inline_query(
        inline_query_id=update.inline_query.id,
        results=inline_results
    )
    return True