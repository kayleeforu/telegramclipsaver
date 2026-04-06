from shazamio import Shazam

shazam = Shazam()
async def recognizeSong(file_path: str):
    result = await shazam.recognize(file_path)
    return result