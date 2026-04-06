from shazamio import Shazam
import logging
import traceback

shazam = Shazam()

async def recognizeSong(file_path: str):
    try:
        result = await shazam.recognize(file_path)
        logging.info(f"Shazam raw result type: {type(result)}")
        logging.info(f"Shazam raw result: {result}")
        
        if isinstance(result, tuple):
            result = result[0]
        
        if result and 'track' in result:
            return result
        else:
            return None
    except Exception as e:
        logging.error(f"Shazam recognition failed: {e}")
        logging.error(traceback.format_exc())
        return None