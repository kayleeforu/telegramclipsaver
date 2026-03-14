from telegram import Update, InlineQueryResultCachedVideo, InlineQueryResultCachedMpeg4Gif
from telegram.ext import ContextTypes
from savevid import downloadVideo
import uuid
import subprocess
from count import countAdd
from database import supabase

clearVids = ["rm", "-f", "/home/kaylee/telegramclipsaver/downloadedVideos/*"]

async def processInline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.inline_query.query

    response = supabase.table("savedVideos").select("*").eq("link", link).execute()
    if response.data:
        file = (response.data[0]["file_id"], response.data[0]["has_audio"])
        if file[1]:
            inlineID = InlineQueryResultCachedVideo(
                id = str(uuid.uuid4()),
                video_file_id = file[0],
                title = "Video"
            )

        else:
            inlineID = InlineQueryResultCachedMpeg4Gif(
                id = str(uuid.uuid4()),
                mpeg4_file_id = file[0],
                title = "GIF"
            )

        await context.bot.answer_inline_query(inline_query_id = update.inline_query.id, results = [inlineID]) # Answer Inline

        countAdd() # Downloaded Count + 1

        return


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

            file_id = msg.video.file_id
            file = (file_id, True)

            inlineID = InlineQueryResultCachedVideo(
                    id = str(uuid.uuid4()),
                    video_file_id = file_id,
                    title = "Video"
                )
        else: 
            msg = await context.bot.send_animation(
                chat_id = -1003794009076,
                animation = f
            )

            file_id = msg.animation.file_id
            file = (file_id, False)

            inlineID = InlineQueryResultCachedMpeg4Gif(
                    id = str(uuid.uuid4()),
                    mpeg4_file_id = file_id,
                    title = "GIF"
                )
    subprocess.run(clearVids) # Clear downloadedVideos Folder

    supabase.table("savedVideos").insert({
        "link": link,
        "file_id": file[0],
        "has_audio": file[1]
    }).execute()

    await context.bot.answer_inline_query(inline_query_id = update.inline_query.id, results=[inlineID]) # Answer Inline

    countAdd() # Downloaded Count + 1

    return