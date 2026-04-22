from gallery_dl import config, job
import os
import asyncio
import tempfile
import shutil
from glob import glob
from telegram import InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
import db
import ffmpeg

database = db.database()
gallery_dl_lock = asyncio.Lock()


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


def extractAudio(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
        if not audio_streams:
            return None
        audio_path = file_path.rsplit(".", 1)[0] + ".mp3"
        (
            ffmpeg
            .input(file_path)
            .audio
            .output(audio_path, acodec='libmp3lame')
            .run(overwrite_output=True, quiet=True)
        )
        return audio_path
    except Exception as e:
        print(f"Probe/Audio extract error: {e}")
        return None


async def downloadMediaGroup(context: ContextTypes.DEFAULT_TYPE, link: str):
    tmp_dir = tempfile.mkdtemp()
    loop = asyncio.get_event_loop()

    try:
        async with gallery_dl_lock:
            try:
                config.load()
                config.set(("extractor", "instagram"), "cookies", "cookiesInstagram.txt")
                config.set(("extractor",), "base-directory", tmp_dir)
                await loop.run_in_executor(None, lambda: job.DownloadJob(link).run())
            except Exception as e:
                print(f"Download error: {e}")
                await database.removeLink(link)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return False

        media_objects = []

        for file in sorted(glob(f"{tmp_dir}/**/*", recursive=True)):
            if not os.path.isfile(file):
                continue

            if file.endswith(".gif"):
                file = await loop.run_in_executor(None, gifToMp4, file)
                if not file:
                    continue

            if file.endswith(".mp4"):
                audio_path = await loop.run_in_executor(None, extractAudio, file)
                has_audio = audio_path is not None
                audio_file_id = None

                if has_audio:
                    with open(audio_path, "rb") as af:
                        msg_audio = await context.bot.send_audio(
                            chat_id=-1003794009076,
                            audio=af,
                            title="Audio"
                        )
                    audio_file_id = msg_audio.audio.file_id

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
                    msg = await context.bot.send_video(
                        chat_id=-1003794009076,
                        video=f,
                        supports_streaming=True
                    )
                    files.append((msg.video.file_id, has_audio, audio_file_id))

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

            for index, msg in enumerate(msgs):
                _, m_type, has_audio, audio_file_id = media_objects[index]
                if msg.video:
                    files.append((msg.video.file_id, has_audio, audio_file_id))
                elif msg.photo:
                    files.append((msg.photo[-1].file_id, False, None))
                else:
                    print(f"Warning: skipping message at index {index} — no video or photo found")

        await database.insert(link, files)
        return True

    except Exception as e:
        print(f"Unexpected error: {e}")
        await database.removeLink(link)
        return False

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def processTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link)


async def processInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link)