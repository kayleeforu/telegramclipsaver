from yt_dlp import YoutubeDL

def downloadVideo(url):
    with open("videoid.txt", 'r+') as f:
        count = int(f.read())
        f.seek(0)
        f.write(str(count + 1))
    URL = [url]
    filepath = f"downloadedVideos/video{count}.mp4"
    with YoutubeDL({
        "quiet": True,
        "outtmpl": filepath
        }) as ydl:
        try:
            ydl.download(URL)
        except:
            return None
    return filepath
