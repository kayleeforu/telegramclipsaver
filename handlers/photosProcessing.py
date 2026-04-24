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
import httpx
import re

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
        print(f"Thumbnail extraction error: {e}")
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

SNAPINSTA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def fetchSnapinstaToken(client: httpx.AsyncClient) -> tuple[str, dict]:
    response = await client.get(
        "https://snapinsta.app/",
        headers=SNAPINSTA_HEADERS,
        follow_redirects=True,
    )
    response.raise_for_status()
    match = re.search(
        r'<input[^>]+name=["\']token["\'][^>]+value=["\']([^"\']+)["\']',
        response.text
    )
    if not match:
        match = re.search(
            r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']token["\']',
            response.text
        )

    if not match:
        raise ValueError("Could not find CSRF token on snapinsta.app page")

    token = match.group(1)
    cookies = dict(response.cookies)

    return token, cookies


async def fetchSnapinstaLinks(client: httpx.AsyncClient, instagram_url: str) -> list[str]:
    token, cookies = await fetchSnapinstaToken(client)

    form_data = {
        "url": instagram_url,
        "token": token,
    }
    post_headers = {
        **SNAPINSTA_HEADERS,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://snapinsta.app/",
        "Origin": "https://snapinsta.app",
        "X-Requested-With": "XMLHttpRequest",
    }

    response = await client.post(
        "https://snapinsta.app/action.php",
        data=form_data,
        headers=post_headers,
        cookies=cookies,
        follow_redirects=True,
    )
    response.raise_for_status()

    cdn_links = re.findall(
        r'href=["\']((https?://[^"\']*(?:cdninstagram\.com|fbcdn\.net)[^"\']*?))["\']',
        response.text
    )

    links = [match[0] for match in cdn_links if match[0]]

    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    return unique_links


async def downloadInstagramWithSnapinsta(link: str, tmp_dir: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30) as client:

        print(f"[snapinsta] Fetching CDN links for: {link}")
        cdn_links = await fetchSnapinstaLinks(client, link)

        if not cdn_links:
            raise ValueError(f"snapinsta returned no download links for: {link}")

        print(f"[snapinsta] Found {len(cdn_links)} media item(s)")

        downloaded = []

        for idx, cdn_url in enumerate(cdn_links):
            url_path = cdn_url.split("?")[0]
            ext = os.path.splitext(url_path)[1].lower()

            if ext not in (".mp4", ".jpg", ".jpeg", ".png", ".webp"):
                ext = ".mp4"

            dest_path = os.path.join(tmp_dir, f"media_{idx:03d}{ext}")
            async with client.stream("GET", cdn_url, headers=SNAPINSTA_HEADERS) as stream:
                stream.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in stream.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

            print(f"[snapinsta] Downloaded: {dest_path}")
            downloaded.append(dest_path)

    return sorted(downloaded)

async def downloadMediaGroup(context: ContextTypes.DEFAULT_TYPE, link: str):
    tmp_dir = tempfile.mkdtemp()
    loop = asyncio.get_event_loop()

    try:
        is_instagram = "instagram.com" in link

        if is_instagram:
            try:
                await downloadInstagramWithSnapinsta(link, tmp_dir)
            except Exception as e:
                print(f"[snapinsta] Download failed: {e}")
                await database.removeLink(link)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return False

        else:
            async with gallery_dl_lock:
                try:
                    config.load()
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
                audio_path, thumb_path = await asyncio.gather(
                    loop.run_in_executor(None, extractAudio, file),
                    loop.run_in_executor(None, extractThumbnail, file),
                )
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