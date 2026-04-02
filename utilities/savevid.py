from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
import os
from PIL import Image

def duration_filter(info):
    duration = info.get("duration")
    if duration and duration > 3600:
        return "Video is too long (max 3600 seconds)"

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

def downloadVideo(url):
    ydl_opts = {
        "quiet": False,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "match_filter": duration_filter,
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

            is_live = info.get("is_live")

            if is_live:
                stream_url = info.get("url")
                video_id = info.get("id")

                output_path = f"downloadedVideos/video{video_id}.mp4"

                (
                    ffmpeg
                    .input(stream_url)
                    .output(output_path, t=30, c="copy")
                    .run(overwrite_output=True)
                )

                thumbnailpath = None

                return output_path, True, thumbnailpath, None, None

            else:
                info = ydl.extract_info(url, download=True)

                filepath = ydl.prepare_filename(info)
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"

                thumbnailpath = convertThumbnail(filepath)

                height = info.get("height", 0)
                width = info.get("width", 0)

                probe = ffmpeg.probe(filepath)
                audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]

                if audio_streams == []:
                    return filepath, False, thumbnailpath, height, width

                return filepath, True, thumbnailpath, height, width

    except DownloadError as e:
        if "too long" in str(e).lower():
            return "too_long", None, None, None, None
        print(f"Error: {e}")
        return None, None, None, None, None

    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None