import asyncio
import os
from shazamio import Shazam

shazam = Shazam()

async def recognizeSong(filename: str) -> dict:
    if filename.endswith((".mp3", ".ogg", ".m4a")):
        return await shazam.recognize(filename)

    audioPath = f"temp_fast_{os.path.basename(filename)}.mp3"
    
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", filename,
            "-vn", "-acodec", "mp3", "-ar", "44100",
            audioPath,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.STDOUT
        )
        
        await process.wait()

        if os.path.exists(audioPath):
            return await shazam.recognize(audioPath)
        return {}

    except Exception as e:
        print(f"Error in recognizeSong: {e}")
        return {}

    finally:
        if os.path.exists(audioPath):
            os.remove(audioPath)