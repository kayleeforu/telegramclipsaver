from yt_dlp import YoutubeDL

def duration_filter(info):
    duration = info.get("duration")
    if duration and duration > 1500:
        return "too_long"

def downloadVideo(url):
    ydl_opts = {
        "quiet": False,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "match_filter": duration_filter,
        "format": "bestvideo[height<=1080][fps<=30]+bestaudio/bestvideo[height<=720]+bestaudio/best",
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
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if filepath.endswith(".webm") or filepath.endswith(".mkv"):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"


            return str(filepath)
    except Exception as e:
        print(f"Error: {e}")
        return None
