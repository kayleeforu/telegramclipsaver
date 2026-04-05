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
            try:
                with Image.open(path) as img:
                    img.convert("RGB").save(jpg_path)
                if ext != "jpg":
                    os.remove(path)
                return jpg_path
            except Exception:
                return None
    return None

def downloadThumbnail(info):
    try:
        thumbnails = info.get("thumbnails")
        video_id = info.get("id")
        if not thumbnails or not video_id:
            return None
        thumb_url = thumbnails[-1]["url"]
        thumb_path = f"downloadedVideos/video{video_id}_thumb.jpg"
        r = requests.get(thumb_url, timeout=5)
        with open(thumb_path, "wb") as f:
            f.write(r.content)
        return thumb_path
    except Exception:
        return None

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": "best[ext=mp4][height<=720]/bestvideo[vcodec^=avc1][height<=720]+bestaudio[ext=m4a]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "cookiefile": "cookies.txt",
        "writethumbnail": False,
        "concurrent_fragment_downloads": 10,
        "buffersize": 1024 * 256,
        "http_chunk_size": 1024 * 1024 * 20,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "web"],
            }
        },
    }

    try:
        if not os.path.exists("downloadedVideos"):
            os.makedirs("downloadedVideos")

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            duration = info.get("duration", 0)
            if duration > 3600:
                return "too_long", None, None, None, None

            video_id = info.get("id")
            thumbnailpath = downloadThumbnail(info)
            
            if info.get("is_live"):
                output_path = f"downloadedVideos/video{video_id}.mp4"
                stream_url = info.get("url")
                (
                    ffmpeg
                    .input(stream_url)
                    .output(output_path, t=30, c="copy")
                    .run(overwrite_output=True, quiet=True)
                )
                return output_path, True, thumbnailpath, info.get("height"), info.get("width")

            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            
            if not os.path.exists(filepath):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            converted_thumb = convertThumbnail(filepath)
            if converted_thumb:
                thumbnailpath = converted_thumb

            hasAudio = False
            if "requested_formats" in info:
                hasAudio = any(f.get('acodec') != 'none' for f in info['requested_formats'])
            else:
                hasAudio = info.get('acodec') != 'none'

            return filepath, hasAudio, thumbnailpath, info.get("height"), info.get("width")

    except DownloadError as e:
        print(f"DownloadError: {e}")
        return None, None, None, None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None