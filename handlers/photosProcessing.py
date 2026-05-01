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
import logging
from utilities.savevid import downloadVideo as ytdlpDownloadVideo

database = db.database()
gallery_dl_lock = asyncio.Lock()


def needsReencode(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        video_streams = [s for s in probe["streams"] if s.get("codec_type") == "video"]
        if not video_streams:
            return True
        vcodec = video_streams[0].get("codec_name", "")
        pix_fmt = video_streams[0].get("pix_fmt", "")
        return not (vcodec == "h264" and pix_fmt == "yuv420p")
    except Exception as e:
        logging.warning(f"needsReencode probe failed for {file_path}: {e} — will re-encode")
        return True


def reencodeVideo(input_path):
    try:
        output_path = input_path.rsplit(".", 1)[0] + "_reenc.mp4"
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec='libx264',
                acodec='aac',
                pix_fmt='yuv420p',
                movflags='faststart',
                crf=24,
                preset='fast'
            )
            .run(overwrite_output=True, quiet=True)
        )
        if os.path.exists(input_path):
            os.remove(input_path)
        return output_path
    except Exception as e:
        logging.error(f"Re-encode error: {e}")
        return input_path


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
        logging.error(f"GIF to MP4 error: {e}")
        return None


def extractThumbnail(video_path):
    try:
        thumb_path = video_path.rsplit(".", 1)[0] + "_thumb.jpg"
        (
            ffmpeg
            .input(video_path, ss=0)
            .output(thumb_path, vframes=1)
            .run(overwrite_output=True, quiet=True)
        )
        return thumb_path if os.path.exists(thumb_path) else None
    except Exception as e:
        logging.error(f"Thumbnail extraction error: {e}")
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
        logging.error(f"Audio extraction error: {e}")
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
                logging.error(f"gallery-dl download error: {e}")
                await database.removeLink(link)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return False

        media_objects = []
        found_missing_audio = False

        for file in sorted(glob(f"{tmp_dir}/**/*", recursive=True)):
            if not os.path.isfile(file):
                continue

            if file.endswith(".gif"):
                file = await loop.run_in_executor(None, gifToMp4, file)
                if not file:
                    continue

            if file.endswith(".mp4"):
                should_reencode = await loop.run_in_executor(None, needsReencode, file)
                if should_reencode:
                    logging.info(f"Re-encoding {os.path.basename(file)}")
                    file = await loop.run_in_executor(None, reencodeVideo, file)

                audio_path, thumb_path = await asyncio.gather(
                    loop.run_in_executor(None, extractAudio, file),
                    loop.run_in_executor(None, extractThumbnail, file),
                )

                if audio_path is None:
                    logging.warning(f"No audio found in gallery-dl result for {link}")
                    found_missing_audio = True

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

                media_objects.append((file, "video", has_audio, audio_file_id, thumb_path))

            elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
                media_objects.append((file, "photo", False, None, None))

        if found_missing_audio:
            logging.info(f"Falling back to yt-dlp for {link}")

            media_objects = []

            yt_filepath, yt_hasAudio, yt_audioPath, yt_thumb, _, _ = \
                await loop.run_in_executor(None, lambda: ytdlpDownloadVideo(link))

            if not yt_filepath:
                logging.error(f"yt-dlp fallback failed entirely for {link}")
                await database.removeLink(link)
                return False

            should_reencode = await loop.run_in_executor(None, needsReencode, yt_filepath)
            if should_reencode:
                logging.info(f"Re-encoding yt-dlp result for {link}")
                yt_filepath = await loop.run_in_executor(None, reencodeVideo, yt_filepath)

            yt_audio_file_id = None
            if yt_hasAudio and yt_audioPath:
                with open(yt_audioPath, "rb") as af:
                    msg_audio = await context.bot.send_audio(
                        chat_id=-1003794009076,
                        audio=af,
                        title="Audio"
                    )
                yt_audio_file_id = msg_audio.audio.file_id
            media_objects.append((yt_filepath, "video", yt_hasAudio, yt_audio_file_id, yt_thumb))

        if not media_objects:
            await database.removeLink(link)
            return False

        files = []

        if len(media_objects) == 1:
            file_path, m_type, has_audio, audio_file_id, thumb_path = media_objects[0]
            with open(file_path, "rb") as f:
                if m_type == "photo":
                    msg = await context.bot.send_photo(chat_id=-1003794009076, photo=f)
                    files.append((msg.photo[-1].file_id, False, None))
                else:
                    thumb_file = open(thumb_path, "rb") if thumb_path else None
                    try:
                        msg = await context.bot.send_video(
                            chat_id=-1003794009076,
                            video=f,
                            supports_streaming=True,
                            thumbnail=thumb_file
                        )
                    finally:
                        if thumb_file:
                            thumb_file.close()
                    files.append((msg.video.file_id, has_audio, audio_file_id))

        else:
            media_group = []
            for file_path, m_type, has_audio, audio_file_id, thumb_path in media_objects:
                if m_type == "photo":
                    media_group.append(InputMediaPhoto(open(file_path, "rb")))
                else:
                    thumb_file = open(thumb_path, "rb") if thumb_path else None
                    media_group.append(
                        InputMediaVideo(
                            open(file_path, "rb"),
                            supports_streaming=True,
                            thumbnail=thumb_file
                        )
                    )

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

            for item in media_group:
                try:
                    item.media.close()
                    if hasattr(item, 'thumbnail') and item.thumbnail:
                        item.thumbnail.close()
                except Exception:
                    pass

            for index, msg in enumerate(msgs):
                _, m_type, has_audio, audio_file_id, _ = media_objects[index]
                if msg.video:
                    files.append((msg.video.file_id, has_audio, audio_file_id))
                elif msg.photo:
                    files.append((msg.photo[-1].file_id, False, None))
                else:
                    logging.warning(f"Skipping message at index {index} — no video or photo")

        await database.insert(link, files)
        return True

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await database.removeLink(link)
        return False

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def processTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link)


async def processInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link)