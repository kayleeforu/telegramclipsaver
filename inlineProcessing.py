from telegram import Update, InlineQueryResultCachedVideo, InlineQueryResultCachedMpeg4Gif
from telegram.ext import ContextTypes
from savevid import downloadVideo
import uuid
import subprocess
from count import countAdd

clearVids = ["rm", "/downloadedVideos/*"]
async def processInline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.inline_query.query

    (filepath, hasAudio) = downloadVideo(link)
    if filepath is None:
        subprocess.run(clearVids)
        return
    
    with open(filepath, "rb") as f:
        if hasAudio:
            msg = await context.bot.send_video(
                chat_id = -1003794009076,
                video = f,
                supports_streaming = True
            )
            inlineID = InlineQueryResultCachedVideo(
                id = str(uuid.uuid4()),
                video_file_id = msg.video.file_id,
                title = "Video"
                )
        else: 
            msg = await context.bot.send_animation(
                chat_id = -1003794009076,
                animation = f
            )
            inlineID = InlineQueryResultCachedMpeg4Gif(
                id = str(uuid.uuid4()),
                mpeg4_file_id = msg.animation.file_id,
                title = "GIF"
                )
    subprocess.run(clearVids)

    await context.bot.answer_inline_query(inline_query_id = update.inline_query.id, results=[inlineID])

    countAdd()

    return