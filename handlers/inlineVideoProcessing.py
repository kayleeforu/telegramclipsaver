from telegram import Update, InlineQueryResultCachedVideo, InlineQueryResultCachedMpeg4Gif
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
import uuid
import subprocess
import asyncio
import logging
from utilities.count import countAdd
import db

clearVids = ["rm", "-f", "downloadedVideos/*"]
database = db.database()

async def processInline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.inline_query.from_user
    userID = user.id

    response = await database.lookUpUser(userID)
    if not response.data:
        username = user.username or "NULL"
        await database.insertUser(userID, username)

    link = update.inline_query.query
    response = await database.lookUpLink(link)
    if response.data:
        file = (response.data[0]["file_ids"][0], response.data[0]["has_audio"][0])
        if file[0] == "processing":
            return
        elif file[1]:
            inlineID = InlineQueryResultCachedVideo(
                id=str(uuid.uuid4()),
                video_file_id=file[0],
                title="Video"
            )
        else:
            inlineID = InlineQueryResultCachedMpeg4Gif(
                id=str(uuid.uuid4()),
                mpeg4_file_id=file[0],
                title="GIF"
            )
        await context.bot.answer_inline_query(inline_query_id=update.inline_query.id, results=[inlineID])
        await countAdd()
        return

    await database.insert(link, ("processing", False))

    loop = asyncio.get_event_loop()
    (filepath, hasAudio, thumbnailpath, height, width) = await loop.run_in_executor(
        None, lambda: downloadVideo(link)
    )

    if filepath is None:
        subprocess.run(clearVids)
        return

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
                logging.info(f"[processInline] video={msg.video}, document={msg.document}, animation={msg.animation}")
                if msg.video:
                    file_id = msg.video.file_id
                elif msg.document:
                    file_id = msg.document.file_id
                else:
                    logging.error("[processInline] Telegram returned message with no video/document")
                    return
                file = (file_id, True)
                inlineID = InlineQueryResultCachedVideo(
                    id=str(uuid.uuid4()),
                    video_file_id=file_id,
                    title="Video"
                )
            else:
                msg = await context.bot.send_animation(
                    chat_id=-1003794009076,
                    animation=f,
                    thumbnail=thumbnailpath,
                    height=height,
                    width=width
                )
                logging.info(f"[processInline] video={msg.video}, document={msg.document}, animation={msg.animation}")
                if msg.animation:
                    file_id = msg.animation.file_id
                elif msg.document:
                    file_id = msg.document.file_id
                else:
                    logging.error("[processInline] Telegram returned message with no animation/document")
                    return
                file = (file_id, False)
                inlineID = InlineQueryResultCachedMpeg4Gif(
                    id=str(uuid.uuid4()),
                    mpeg4_file_id=file_id,
                    title="GIF"
                )
    except Exception as e:
        logging.error(f"[processInline] Error sending to Telegram: {e}")
        return
    finally:
        subprocess.run(clearVids)
        await database.removeLink(link)

    await database.insert(link, file)
    await context.bot.answer_inline_query(inline_query_id=update.inline_query.id, results=[inlineID])
    await countAdd()