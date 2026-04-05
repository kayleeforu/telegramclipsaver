from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
import os
from PIL import Image
import requests


def convertThumbnail(filepath):
    base = filepath.rsplit(".", 1)[0]
    for ext in ["webp", "jpg", "jpeg", "png"]:
        path = f"{base}.{ext}"
        if os.path.exists(path):
            jpg_path = base + ".jpg"
            Image.open(path).convert("RGB").save(jpg_path)
            if ext != "jpg":
                os.remove(path)
            return jpg_path
    return None


def downloadThumbnail(info):
    try:
        thumbnails = info.get("thumbnails")
        video_id = info.get("id")

        if not thumbnails or not video_id:
            return None

        thumb_url = thumbnails[-1]["url"]
        thumb_path = f"downloadedVideos/video{video_id}_thumb.jpg"

        r = requests.get(thumb_url, timeout=10)
        r.raise_for_status()

        with open(thumb_path, "wb") as f:
            f.write(r.content)

        return thumb_path
    except Exception:
        return None


def downloadVideo(url):
    ydl_opts = {
        "quiet": False,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": (
            "bv*[ext=mp4][height<=720][vcodec^=avc1]+ba[ext=m4a]/"
            "b[ext=mp4][height<=720]/"
            "best[height<=720]"
        ),
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
        "writethumbnail": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
            }
        },
        "concurrent_fragment_downloads": 4,
        "http_chunk_size": 1024 * 1024 * 10,
        "buffersize": 1024 * 64,
        "noplaylist": True,
        "hls_prefer_native": False,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                return "no_info", None, None, None, None

            duration = info.get("duration")
            height = info.get("height", 0)
            width = info.get("width", 0)

            if duration and duration > 3600:
                return "too_long", None, None, None, None

            formats = info.get("formats") or []
            if not formats:
                return "drm_blocked", None, None, None, None

            thumbnailpath = downloadThumbnail(info)

            if info.get("is_live"):
                stream_url = info.get("url")
                video_id = info.get("id")
                output_path = f"downloadedVideos/video{video_id}.mp4"

                (
                    ffmpeg
                    .input(stream_url)
                    .output(output_path, t=30, c="copy")
                    .run(overwrite_output=True)
                )

                return output_path, True, thumbnailpath, None, None

            info = ydl.extract_info(url, download=True)

            filepath = ydl.prepare_filename(info)
            filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            converted_thumb = convertThumbnail(filepath)
            if converted_thumb:
                thumbnailpath = converted_thumb

            height = info.get("height", height)
            width = info.get("width", width)

            probe = ffmpeg.probe(filepath)
            audio_streams = [
                s for s in probe["streams"] if s["codec_type"] == "audio"
            ]

            hasAudio = len(audio_streams) > 0

            return filepath, hasAudio, thumbnailpath, height, width

    except DownloadError as e:
        err = str(e)

        if "DRM" in err or "protected" in err:
            return "drm_blocked", None, None, None, None

        if "403" in err:
            return "access_denied", None, None, None, None

        print(f"DownloadError: {e}")
        return None, None, None, None, None

    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None