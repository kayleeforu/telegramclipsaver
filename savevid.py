from yt_dlp import YoutubeDL

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
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
            return str(filepath)
    except Exception as e:
        print(f"Error: {e}")
        return None