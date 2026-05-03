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

database = db.database()
gallery_dl_lock = asyncio.Lock()


def gifToMp4(gif_path):
    logging.info(f"[gifToMp4] Converting GIF to MP4: {gif_path}")
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
        logging.info(f"[gifToMp4] Done: {mp4path}")
        return mp4path
    except Exception as e:
        logging.info(f"[gifToMp4] Error: {e}")
        return None


def reencodeIfNeeded(video_path):
    logging.info(f"[reencodeIfNeeded] Probing: {video_path}")
    try:
        probe = ffmpeg.probe(video_path)
        video_streams = [s for s in probe["streams"] if s.get("codec_type") == "video"]
        if not video_streams:
            logging.info(f"[reencodeIfNeeded] No video streams found, skipping: {video_path}")
            return video_path

        codec = video_streams[0].get("codec_name", "")
        logging.info(f"[reencodeIfNeeded] Detected codec: {codec}")
        out_path = video_path.rsplit(".", 1)[0] + "_out.mp4"

        if codec == "h264":
            logging.info(f"[reencodeIfNeeded] Already H.264, remuxing with faststart: {video_path}")
            (
                ffmpeg
                .input(video_path)
                .output(out_path, vcodec="copy", acodec="copy", movflags="+faststart")
                .run(overwrite_output=True, quiet=True)
            )
        else:
            logging.info(f"[reencodeIfNeeded] Re-encoding from {codec} to H.264: {video_path}")
            (
                ffmpeg
                .input(video_path)
                .output(out_path, vcodec="libx264", pix_fmt="yuv420p", acodec="aac", movflags="+faststart", preset="ultrafast", crf="28")
                .run(overwrite_output=True, quiet=True)
            )

        if os.path.exists(video_path):
            os.remove(video_path)
        logging.info(f"[reencodeIfNeeded] Done: {out_path}")
        return out_path

    except Exception as e:
        logging.info(f"[reencodeIfNeeded] Error: {e}")
        return video_path


def extractThumbnail(video_path):
    logging.info(f"[extractThumbnail] Extracting thumbnail from: {video_path}")
    try:
        thumb_path = video_path.rsplit(".", 1)[0] + "_thumb.jpg"
        (
            ffmpeg
            .input(video_path, ss=0)
            .output(thumb_path, vframes=1)
            .run(overwrite_output=True, quiet=True)
        )
        result = thumb_path if os.path.exists(thumb_path) else None
        logging.info(f"[extractThumbnail] Result: {result}")
        return result
    except Exception as e:
        logging.info(f"[extractThumbnail] Error: {e}")
        return None


def extractAudio(file_path):
    logging.info(f"[extractAudio] Probing audio from: {file_path}")
    try:
        probe = ffmpeg.probe(file_path)
        audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
        if not audio_streams:
            logging.info(f"[extractAudio] No audio streams found: {file_path}")
            return None
        audio_path = file_path.rsplit(".", 1)[0] + ".mp3"
        logging.info(f"[extractAudio] Extracting audio to: {audio_path}")
        (
            ffmpeg
            .input(file_path)
            .audio
            .output(audio_path, acodec='libmp3lame')
            .run(overwrite_output=True, quiet=True)
        )
        logging.info(f"[extractAudio] Done: {audio_path}")
        return audio_path
    except Exception as e:
        logging.info(f"[extractAudio] Error: {e}")
        return None


async def downloadMediaGroup(context: ContextTypes.DEFAULT_TYPE, link: str):
    logging.info(f"[downloadMediaGroup] Starting for link: {link}")
    tmp_dir = tempfile.mkdtemp()
    logging.info(f"[downloadMediaGroup] Temp dir: {tmp_dir}")
    loop = asyncio.get_event_loop()

    try:
        async with gallery_dl_lock:
            logging.info(f"[downloadMediaGroup] Acquired gallery_dl_lock, starting download")
            try:
                config.load()
                config.set(("extractor", "instagram"), "cookies", "cookiesInstagram.txt")
                config.set(("extractor",), "base-directory", tmp_dir)
                await loop.run_in_executor(None, lambda: job.DownloadJob(link).run())
                logging.info(f"[downloadMediaGroup] gallery-dl download finished")
            except Exception as e:
                logging.info(f"[downloadMediaGroup] Download error: {e}")
                await database.removeLink(link)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return False

        files_found = []
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                files_found.append(os.path.join(root, f))
        files_found.sort()
        logging.info(f"[downloadMediaGroup] Files found after download: {files_found}")

        media_objects = []

        for file in files_found:
            if not os.path.isfile(file):
                continue

            logging.info(f"[downloadMediaGroup] Processing file: {file}")

            if file.endswith(".gif"):
                logging.info(f"[downloadMediaGroup] GIF detected, converting: {file}")
                file = await loop.run_in_executor(None, gifToMp4, file)
                if not file:
                    logging.info(f"[downloadMediaGroup] GIF conversion failed, skipping")
                    continue

            if file.endswith(".mp4"):
                logging.info(f"[downloadMediaGroup] MP4 detected, running reencodeIfNeeded: {file}")
                file = await loop.run_in_executor(None, reencodeIfNeeded, file)
                logging.info(f"[downloadMediaGroup] reencodeIfNeeded returned: {file}")

                logging.info(f"[downloadMediaGroup] Extracting audio and thumbnail for: {file}")
                audio_path, thumb_path = await asyncio.gather(
                    loop.run_in_executor(None, extractAudio, file),
                    loop.run_in_executor(None, extractThumbnail, file),
                )
                logging.info(f"[downloadMediaGroup] audio_path={audio_path}, thumb_path={thumb_path}")
                has_audio = audio_path is not None
                audio_file_id = None

                if has_audio:
                    logging.info(f"[downloadMediaGroup] Uploading audio to Telegram")
                    with open(audio_path, "rb") as af:
                        msg_audio = await context.bot.send_audio(
                            chat_id=-1003794009076,
                            audio=af,
                            title="Audio"
                        )
                    audio_file_id = msg_audio.audio.file_id
                    logging.info(f"[downloadMediaGroup] Audio uploaded, file_id: {audio_file_id}")

                media_objects.append((file, "video", has_audio, audio_file_id, thumb_path))

            elif file.endswith((".jpg", ".jpeg", ".png", ".webp")):
                logging.info(f"[downloadMediaGroup] Image file detected: {file}")
                media_objects.append((file, "photo", False, None, None))

        logging.info(f"[downloadMediaGroup] Total media objects: {len(media_objects)}")

        if not media_objects:
            logging.info(f"[downloadMediaGroup] No media objects, removing link")
            await database.removeLink(link)
            return False

        files = []

        if len(media_objects) == 1:
            file_path, m_type, has_audio, audio_file_id, thumb_path = media_objects[0]
            logging.info(f"[downloadMediaGroup] Single media, uploading: {file_path}, type={m_type}")
            with open(file_path, "rb") as f:
                if m_type == "photo":
                    msg = await context.bot.send_photo(chat_id=-1003794009076, photo=f)
                    files.append((msg.photo[-1].file_id, False, None))
                    logging.info(f"[downloadMediaGroup] Photo sent")
                else:
                    thumb_file = open(thumb_path, "rb") if thumb_path else None
                    try:
                        msg = await context.bot.send_video(
                            chat_id=-1003794009076,
                            video=f,
                            supports_streaming=True,
                            thumbnail=thumb_file
                        )
                        logging.info(f"[downloadMediaGroup] Video sent")
                    finally:
                        if thumb_file:
                            thumb_file.close()
                    files.append((msg.video.file_id, has_audio, audio_file_id))

        else:
            logging.info(f"[downloadMediaGroup] Multiple media, building media group")
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
                logging.info(f"[downloadMediaGroup] Sending media group chunk {i} to {i + len(chunk)}")
                chunk_msgs = await context.bot.send_media_group(
                    chat_id=-1003794009076,
                    media=chunk
                )
                msgs.extend(chunk_msgs)
                logging.info(f"[downloadMediaGroup] Chunk sent, {len(chunk_msgs)} messages")
                if i + 10 < len(media_group):
                    logging.info(f"[downloadMediaGroup] Sleeping 5s before next chunk")
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
                    logging.info(f"[downloadMediaGroup] Warning: skipping message at index {index} — no video or photo found")

        logging.info(f"[downloadMediaGroup] Inserting {len(files)} files into database for link: {link}")
        await database.insert(link, files)
        logging.info(f"[downloadMediaGroup] Done for link: {link}")
        return True

    except Exception as e:
        logging.info(f"[downloadMediaGroup] Unexpected error: {e}")
        await database.removeLink(link)
        return False

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logging.info(f"[downloadMediaGroup] Cleaned up temp dir: {tmp_dir}")


async def processTikTokSlideshow(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link)


async def processInstagramPost(context: ContextTypes.DEFAULT_TYPE, link: str):
    return await downloadMediaGroup(context, link)