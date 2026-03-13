from yt_dlp import YoutubeDL
import subprocess
import os

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": "bv*[height<=1080]+ba/b",
        "merge_output_format": "mp4",
        "cookiefile": "/home/ubuntu/bot/cookies.txt",
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
            }
        },
        "fragment_retries": 10,
        "remote_components": ["ejs:github"],
        "concurrent_fragment_downloads": 4,
        "buffersize": 1024,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if filepath.endswith(".webm") or filepath.endswith(".mkv"):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"
            
            compressed = filepath.replace(".mp4", "_compressed.mp4")
            subprocess.run([
                "ffmpeg", "-i", filepath,
                "-crf", "29",
                "-preset", "fast",
                "-vcodec", "libx264",
                "-acodec", "aac",
                compressed, "-y"
            ], check=True)
            
            os.remove(filepath)

            return str(compressed)
    except Exception:
        return None