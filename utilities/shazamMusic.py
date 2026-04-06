import asyncio
import os
from shazamio import Shazam

shazam = Shazam()

async def recognizeSong(filename: str) -> dict:
    if filename.endswith((".mp3", ".ogg", ".m4a")):
        try:
            with open(filename, "rb") as f:
                audio_bytes = f.read()
                
            if hasattr(shazam, 'recognize'):
                return await shazam.recognize(audio_bytes)
            else:
                return await shazam.recognize_song(audio_bytes)
        except Exception as e:
            print(f"Direct recognize error: {e}")
            return {}

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
            with open(audioPath, "rb") as f:
                audio_bytes = f.read()
                
            if hasattr(shazam, 'recognize'):
                return await shazam.recognize(audio_bytes)
            else:
                return await shazam.recognize_song(audio_bytes)
                
        return {}

    except Exception as e:
        print(f"Error in recognizeSong (ffmpeg fallback): {e}")
        return {}

    finally:
        if os.path.exists(audioPath):
            os.remove(audioPath)