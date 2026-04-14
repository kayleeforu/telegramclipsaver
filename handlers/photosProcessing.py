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

    media_objects = []

    for file in sorted(glob(f"{directory}/**/*", recursive=True)):
        if not os.path.isfile(file):
            continue

        if file.endswith(".gif"):
            new_file = gifToMp4(file)
            if not new_file:
                continue
            file = new_file

        if file.endswith(".mp4"):
            has_audio = False
            audio_file_id = None
            try:
                probe = ffmpeg.probe(file)
                audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
                if len(audio_streams) > 0:
                    audio_path = file.rsplit(".", 1)[0] + ".mp3"
                    # Extract audio track
                    (
                        ffmpeg
                        .input(file)
                        .audio
                        .output(audio_path, acodec='libmp3lame')
                        .run(overwrite_output=True, quiet=True)
                    )
                    # Upload audio to cache channel
                    msg_audio = await context.bot.send_audio(
                        chat_id=-1003794009076,
                        audio=open(audio_path, "rb"),
                        title="Audio"
                    )
                    audio_file_id = msg_audio.audio.file_id
                    has_audio = True
            except Exception as e:
                print(f"Probe/Audio extract error: {e}")

            media_objects.append((file, "video", has_audio, audio_file_id))

        elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media_objects.append((file, "photo", False, None))

    if not media_objects:
        await database.removeLink(link)
        return False

    files = []
    if len(media_objects) == 1:
        file_path, m_type, has_audio, audio_file_id = media_objects[0]
        with open(file_path, "rb") as f:
            if m_type == "photo":
                msg = await context.bot.send_photo(chat_id=-1003794009076, photo=f)
                files.append((msg.photo[-1].file_id, False, None))
            else:
                if has_audio:
                    msg = await context.bot.send_video(chat_id=-1003794009076, video=f, supports_streaming=True)
                    files.append((msg.video.file_id, True, audio_file_id))
                else:
                    msg = await context.bot.send_animation(chat_id=-1003794009076, animation=f)
                    files.append((msg.animation.file_id, False, None))
    
    else:
        media_group = []
        for file_path, m_type, has_audio, audio_file_id in media_objects:
            if m_type == "photo":
                media_group.append(InputMediaPhoto(open(file_path, "rb")))
            else:
                media_group.append(InputMediaVideo(open(file_path, "rb"), supports_streaming=True))
        
        msgs = []
        for i in range(0, len(media_group), 10):
            chunk = media_group[i:i + 10]
            chunk_msgs = await context.bot.send_media_group(
                chat_id=-1003794009076,
                media=chunk
            )
            msgs.extend(chunk_msgs)
            if i + 10 < len(media_group):
                await asyncio.sleep(5)
        
        for index, entry in enumerate(msgs):
            _, m_type, has_audio, audio_file_id = media_objects[index]
            if entry.video:
                files.append((entry.video.file_id, has_audio, audio_file_id))
            else:
                files.append((entry.photo[-1].file_id, False, None))

    clearFolder(directory)
    await database.insert(link, files)
    return True

async def processTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link, SLIDESHOW_DIR)

async def processInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link, INSTAGRAM_DIR)