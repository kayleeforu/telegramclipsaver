from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
from utilities.getVideoInfo import getVideoInfo

def duration_filter(info):
    duration = info.get("duration")
    if duration and duration > 39600:
        return "Video is too long (max 39600 seconds)"

async def downloadVideo(url):
    try:
        with YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        duration = info.get("duration", 0)

        if duration >= 1800:
            chosen_format = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        else:
            chosen_format = "bestvideo[vcodec^=avc][height<=1080]+bestaudio/bestvideo[height<=1080]+bestaudio/best"

        ydl_opts = {
            "quiet": False,
            "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
            "match_filter": duration_filter,

            "format": chosen_format,
            "merge_output_format": "mp4",

            "cookiefile": "cookies.txt",
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "web_safari"],
                }
            },

            "concurrent_fragment_downloads": 5,
            "fragment_retries": 10,
            "buffersize": 8192,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            filepath = ydl.prepare_filename(info)
            filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            thumbnailpath, height, width = await getVideoInfo(str(filepath))

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