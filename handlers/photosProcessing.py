from gallery_dl import config, job
import os
import asyncio
from glob import glob
from telegram import InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db
import ffmpeg

database = db.database()

SLIDESHOW_DIR = "tiktok-slideshow"
INSTAGRAM_DIR = "instagram-downloads"

os.makedirs(SLIDESHOW_DIR, exist_ok=True)
os.makedirs(INSTAGRAM_DIR, exist_ok=True)


def clearFolder(directory):
    for file in glob(f"{directory}/**/*", recursive=True):
        if os.path.isfile(file):
            os.remove(file)

def gifToMp4(gif_path):
    try:
        mp4path = gif_path.rsplit(".", 1)[0] + ".mp4"
        (
            ffmpeg
            .input(gif_path)
            .output(mp4path, vcodec='libx264', pix_fmt='yuv420p')
            .run(overwrite_output=True, quiet=True)
        )
        if os.path.exists(gif_path):
            os.remove(gif_path)
        return mp4path
    except Exception as e:
        print(f"Error converting GIF to MP4: {e}")
        return None


async def downloadMediaGroup(context: ContextTypes.DEFAULT_TYPE, link: str, directory: str):
    clearFolder(directory)

    try:
        config.load()
        config.set(("extractor", "instagram"), "cookies", "cookiesInstagram.txt")
        config.set(("extractor",), "base-directory", directory)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: job.DownloadJob(link).run())

    except Exception as e:
        print(f"Download error: {e}")
        await database.removeLink(link)
        return False

    media = []
    has_audio_list = []

    for file in sorted(glob(f"{directory}/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue

        if file.endswith(".gif"):
            newFile = gifToMp4(file)
            if not newFile:
                continue
            file = newFile

        if file.endswith(".mp4"):
            media.append(InputMediaVideo(open(file, "rb"), supports_streaming=True))
            try:
                probe = ffmpeg.probe(file)
                audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
                has_audio_list.append(len(audio_streams) > 0)
            except Exception as e:
                print(f"Probe error: {e}")
                has_audio_list.append(False)

        elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media.append(InputMediaPhoto(open(file, "rb")))
            has_audio_list.append(False)

    if not media:
        await database.removeLink(link)
        return False

    msgs = []

    for i in range(0, len(media), 10):
        chunk = media[i:i + 10]
        chunk_msgs = await context.bot.send_media_group(
            chat_id = -1003794009076,
            media = chunk
        )
        msgs.extend(chunk_msgs)
        if i + 10 < len(media):
            await asyncio.sleep(5)

    files = []
    for index, entry in enumerate(msgs):
        if entry.video:
            files.append((entry.video.file_id, has_audio_list[index]))
        else:
            files.append((entry.photo[-1].file_id, False))

    clearFolder(directory)
    await database.insert(link, files)
    return True

async def processTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link, SLIDESHOW_DIR)

async def processInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link, INSTAGRAM_DIR)