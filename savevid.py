from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg

def duration_filter(info):
    duration = info.get("duration")
    if duration and duration > 600:
        return "Video is too long (max 10 minutes)"

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "match_filter": duration_filter,
        "format": "bestvideo[vcodec^=avc][height<=1080]+bestaudio/bestvideo[height<=1080]+bestaudio/best",
        "merge_output_format": "mp4",
        "cookiefile": "/home/kaylee/telegramclipsaver/cookies.txt",
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "web_safari"],
            }
        },
        "fragment_retries": 10,
        "remote_components": ["ejs:github"],
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
            if filepath.endswith(".webm") or filepath.endswith(".mkv"):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"
                
            probe = ffmpeg.probe(filepath)
            audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
            if audio_streams == []:
                return filepath, False

            return str(filepath), True
    except DownloadError as e:
        if "too long" in str(e).lower() or "max 15 minutes" in str(e).lower():
            return "too_long", None
        print(f"Error: {e}")
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None