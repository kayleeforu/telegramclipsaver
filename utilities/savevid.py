from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
import os
from PIL import Image
import requests


DOWNLOAD_DIR = "downloadedVideos"


def convert_thumbnail(base_path):
    base = base_path.rsplit(".", 1)[0]
    for ext in ["webp", "jpg", "jpeg", "png"]:
        path = f"{base}.{ext}"
        if os.path.exists(path):
            jpg_path = base + ".jpg"
            Image.open(path).convert("RGB").save(jpg_path)
            if ext != "jpg":
                os.remove(path)
            return jpg_path
    return None


def download_thumbnail(info):
    try:
        thumbnails = info.get("thumbnails")
        video_id = info.get("id")

        if not thumbnails or not video_id:
            return None

        thumb_url = thumbnails[-1]["url"]
        thumb_path = f"{DOWNLOAD_DIR}/video{video_id}_thumb.jpg"

        r = requests.get(thumb_url, timeout=10)
        r.raise_for_status()

        with open(thumb_path, "wb") as f:
            f.write(r.content)

        return thumb_path
    except Exception:
        return None


def download_video(url):
    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/video%(id)s.%(ext)s",
        "quiet": False,
        "format": (
            "bv*[ext=mp4][height<=720][vcodec^=avc1]+ba[ext=m4a]/"
            "b[ext=mp4][height<=720]/"
            "best[height<=720]"
        ),
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
            }
        },
        "ignoreerrors": False,
        "concurrent_fragment_downloads": 4,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
        "writethumbnail": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                return "no_info", None, None, None, None

            duration = info.get("duration")
            if duration and duration > 3600:
                return "too_long", None, None, None, None

            formats = info.get("formats") or []
            if not formats:
                return "drm_blocked", None, None, None, None

            thumbnail_path = download_thumbnail(info)

            if info.get("is_live"):
                stream_url = info.get("url")
                video_id = info.get("id")
                output_path = f"{DOWNLOAD_DIR}/video{video_id}.mp4"

                (
                    ffmpeg
                    .input(stream_url)
                    .output(output_path, t=30, c="copy")
                    .run(overwrite_output=True)
                )

                return output_path, True, thumbnail_path, None, None

            info = ydl.extract_info(url, download=True)

            filepath = ydl.prepare_filename(info)
            filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            converted_thumb = convert_thumbnail(filepath)
            if converted_thumb:
                thumbnail_path = converted_thumb

            height = info.get("height")
            width = info.get("width")

            probe = ffmpeg.probe(filepath)
            has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])

            return filepath, has_audio, thumbnail_path, height, width

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