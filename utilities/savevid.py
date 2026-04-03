from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
import os
from PIL import Image
import requests


def convertThumbnail(filepath):
    base = filepath.rsplit(".", 1)[0]
    for ext in ["webp", "jpg", "jpeg", "png", "image"]:
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
            "bestvideo[vcodec^=avc][height<=1080]+bestaudio/"
            "bestvideo[vcodec^=h264][height<=1080]+bestaudio/"
            "bestvideo[height<=1080][ext=mp4]+bestaudio/"
            "best[height<=1080]/"

            "bestvideo[vcodec^=avc][height<=720]+bestaudio/"
            "bestvideo[vcodec^=h264][height<=720]+bestaudio/"
            "bestvideo[height<=720][ext=mp4]+bestaudio/"
            "best[height<=720]/best"
        ),
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
        "writethumbnail": True,
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "web_safari"],
            }
        },
        "remote_components": ["ejs:github"],
        "concurrent_fragment_downloads": 6,
        "http_chunk_size": 1024 * 1024 * 10,
        "buffersize": 1024 * 64,
        "noplaylist": True,
        "hls_prefer_native": False,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            duration = info.get("duration")
            height = info.get("height", 0)
            width = info.get("width", 0)

            thumbnailpath = downloadThumbnail(info)

            if duration:
                if duration > 3600:
                    return "too_long", None, None, None, None

            is_live = info.get("is_live")
            video_id = info.get("id")

            if is_live:
                stream_url = info.get("url")
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
        print(f"DownloadError: {e}")
        return None, None, None, None, None

    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None