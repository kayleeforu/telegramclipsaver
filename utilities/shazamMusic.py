import acoustid
import logging
import os

ACOUSTID_API_KEY = os.environ.get("ACOUSTID_API")

async def recognizeSong(file_path: str):
    try:
        import asyncio
        loop = asyncio.get_running_loop()

        def lookup():
            for score, recording_id, title, artist in acoustid.match(ACOUSTID_API_KEY, file_path):
                return {"title": title, "artist": artist, "recording_id": recording_id}
            return None

        result = await loop.run_in_executor(None, lookup)
        return result

    except Exception as e:
        logging.error(f"AcoustID recognition failed for {file_path}: {e}")
        return None