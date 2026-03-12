from yt_dlp import YoutubeDL

def downloadVideo(url):
    ydl_opts = {
        "quiet": True,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "js_runtimes": {"node": {}}
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

            if filepath.endswith(".webm") or filepath.endswith(".mkv"):
                filepath = filepath.rsplit(".", 1)[0] + ".mp4"

            return filepath

    except Exception:
        return None