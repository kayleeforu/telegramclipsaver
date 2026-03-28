from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
from utilities.getVideoInfo import getVideoInfo

import shutil
import os

def duration_filter(info):
    duration = info.get("duration")
    if duration and duration > 3600:
        return "Video is too long (max 3600 seconds)"

async def downloadVideo(url):
    
    ydl_opts = {
        "quiet": False,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "match_filter": duration_filter,
        "format": "bestvideo[vcodec^=avc][height<=720]+bestaudio/bestvideo[height<=720]+bestaudio/best",
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "web_safari"],
            }
        },
        "remote_components": ["ejs:github"],
        "concurrent_fragment_downloads": 6,
        'http_chunk_size': 1024 * 1024 * 10,
        "buffersize": 1024 * 64,
        "noplaylist": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download = True)

            filepath = ydl.prepare_filename(info)
            filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            thumbnailpath, height, width = await getVideoInfo(filepath)
            shutil.copy(thumbnailpath, f"debug_frame_{os.path.basename(thumbnailpath)}")

            probe = ffmpeg.probe(filepath)
            audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
            if audio_streams == []:
                return filepath, False, thumbnailpath, height, width
            return str(filepath), True, thumbnailpath, height, width

    except DownloadError as e:
        if "too long" in str(e).lower():
            return "too_long", None, None, None, None
        print(f"Error: {e}")
        return None, None, None, None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None