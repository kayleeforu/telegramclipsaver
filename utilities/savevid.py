from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
from utilities.getVideoInfo import getVideoInfo

def duration_filter(info):
    duration = info.get("duration")
    if duration and duration > 1800:
        return "Video is too long (max 1800 seconds)"

async def downloadVideo(url):
    ydl_opts = {
        "quiet": False,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "match_filter": duration_filter,
        "format": "bestvideo[vcodec^=avc][height<=1080]+bestaudio/bestvideo[height<=1080]+bestaudio/best",
        "merge_output_format": "mp4",
        "cookiefile": "/home/kaylee/telegramclipsaver/cookies.txt",
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "tv_embedded", "web"],
            }
        },
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 2,
        "buffersize": 8192,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "postprocessor_args": {
            "ffmpeg": ["-movflags", "+faststart"]
        },
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if filepath.endswith((".webm", ".mkv", ".gif")):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            thumbnailpath, height, width = await getVideoInfo(str(filepath))
            probe = ffmpeg.probe(filepath)
            audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
            return str(filepath), bool(audio_streams), thumbnailpath, height, width

    except DownloadError as e:
        if "too long" in str(e).lower():
            return "too_long", None, None, None, None
        print(f"Error: {e}")
        return None, None, None, None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None