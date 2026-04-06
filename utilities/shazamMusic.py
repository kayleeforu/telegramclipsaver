from shazamio import Shazam

shazam = Shazam()

async def recognizeSong(file_path: str):
    try:
        result = await shazam.recognize(file_path)
        if result and 'track' in result:
            return result
        else:
            return None
    except Exception as e:
        import logging
        logging.error(f"Shazam recognition failed for {file_path}: {e}")
        return None