import subprocess
import asyncio
from shazamio import Shazam

def recognize_song_from_video(filename: str) -> dict:
    audio_path = "temp_audio.mp3"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", filename,
        "-vn",
        "-acodec", "mp3",
        audio_path
    ], check=True)

    async def recognize():
        shazam = Shazam()
        return await shazam.recognize_song(audio_path)

    result = asyncio.run(recognize())
    return result

# TODO REMOVE
if __name__ == "__main__":
    video_file = "input_video.mp4"
    result = recognize_song_from_video(video_file)
    print(result)