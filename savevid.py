from yt_dlp import YoutubeDL

def downloadVideo(url):
    with open("videoid.txt", 'r+') as f:
        count = int(f.read())
        f.seek(0)
        f.write(str(count + 1))
    
    URL = [url]
    filepath = f"downloadedVideos/video{count}.%(ext)s"
    
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
