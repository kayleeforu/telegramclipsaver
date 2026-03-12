from yt_dlp import YoutubeDL

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"]
            }
        }
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