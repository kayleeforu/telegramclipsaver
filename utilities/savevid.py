from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import ffmpeg
import os
from PIL import Image
import requests
from pathlib import Path

def ensureSolverScript():
    solverDir = Path("resources")
    solverPath = solverDir / "yt.solver.lib.min.js"
    
    solverDir.mkdir(exist_ok=True)
    
    if solverPath.exists():
        return str(solverPath)
    
    url = "https://github.com/yt-dlp/ejs/releases/download/0.8.0/yt.solver.lib.min.js"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(solverPath, "wb") as f:
            f.write(response.content)
        
        return str(solverPath)
    
    except Exception as e:
        print(f"Solver download error: {e}")
        return None

def convertThumbnail(filepath):
    base = filepath.rsplit(".", 1)[0]
    for ext in ["webp", "jpg", "jpeg", "png", "image"]:
        path = f"{base}.{ext}"
        if os.path.exists(path):
            jpg_path = base + ".jpg"
            Image.open(path).convert("RGB").save(jpg_path)
            if ext != "jpg":
                os.remove(path)
            return jpg_path
    return None

def downloadThumbnail(info):
    try:
        thumbnails = info.get("thumbnails")
        videoID = info.get("id")
        if not thumbnails or not videoID:
            return None
        thumb_url = thumbnails[-1]["url"]
        thumb_path = f"downloadedVideos/video{videoID}_thumb.jpg"
        r = requests.get(thumb_url, timeout=10)
        with open(thumb_path, "wb") as f:
            f.write(r.content)
        return thumb_path
    except Exception:
        return None

def downloadVideo(url):
    solverPath = ensureSolverScript()
    
    ydl_opts = {
        "quiet": False,
        "outtmpl": "downloadedVideos/video%(id)s.%(ext)s",
        "format": (
            "bestvideo[vcodec^=avc][height<=1080]+bestaudio/"
            "bestvideo[vcodec^=h264][height<=1080]+bestaudio/"
            "bestvideo[height<=1080][ext=mp4]+bestaudio/"
            "best[height<=1080]/best"
        ),
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
        "writethumbnail": True,
        "cache_dir": "yt_dlp_cache",
        "js_runtimes": {"node": {"path": "/usr/bin/node"}},
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "web_safari"],
            }
        },
        "remote_components": {"ejs:github": {"path": solverPath}} if solverPath else {},
        "concurrent_fragment_downloads": 16,
        "http_chunk_size": 1024 * 1024 * 10,
        "buffersize": 1024 * 64,
        "noplaylist": True,
        "hls_prefer_native": False,
        "postprocessor_args": {
            "ffmpeg": ["-crf", "18", "-preset", "slow"]
        },
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            duration = info.get("duration")
            height = info.get("height", 0)
            width = info.get("width", 0)
            
            if duration:
                if duration > 3600:
                    return "too_long", None, None, None, None, None
            
            is_live = info.get("is_live")
            if is_live:
                return None, None, None, None, None, None
            
            filepath = ydl.prepare_filename(info)
            filepath = filepath.rsplit(".", 1)[0] + ".mp4"
            
            thumbnailpath = downloadThumbnail(info)
            converted_thumb = convertThumbnail(filepath)
            if converted_thumb:
                thumbnailpath = converted_thumb
            
            height = info.get("height", height)
            width = info.get("width", width)
            
            probe = ffmpeg.probe(filepath)
            audio_streams = [
                s for s in probe["streams"] if s["codec_type"] == "audio"
            ]
            hasAudio = len(audio_streams) > 0
            audioPath = None
            if hasAudio:
                audioPath = filepath.rsplit(".", 1)[0] + ".mp3"
                ffmpeg.input(filepath).audio.output(
                    audioPath,
                    acodec='libmp3lame'
                ).run(overwrite_output=True, quiet=True)
            return filepath, hasAudio, audioPath, thumbnailpath, height, width
    except DownloadError as e:
        print(f"DownloadError: {e}")
        return None, None, None, None, None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None, None, None