from yt_dlp import YoutubeDL

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": "bv*[height<=720]+ba/b",
        "merge_output_format": "mp4",
        "cookiefile": "/home/ubuntu/bot/cookies.txt",
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
            }
        },
        "retries": 10,
        "fragment_retries": 10,
        "remote_components": ["ejs:github"],
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if filepath.endswith(".webm") or filepath.endswith(".mkv"):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"
            return str(filepath)
    except Exception:
        return None