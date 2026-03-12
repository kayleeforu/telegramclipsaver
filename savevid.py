from yt_dlp import YoutubeDL

def downloadVideo(url):
    URL = [url]
    filepath = "downloadedVideos/video%(id)s.%(ext)s"
    
    with YoutubeDL({
        "quiet": True,
        "outtmpl": filepath,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "js_runtimes": {
            "node": {}
        }
        }) as ydl:
        try:
            ydl.download(URL)
        except:
            return None
    return filepath
