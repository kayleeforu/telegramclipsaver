from supabase import create_client
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

class database:
    def __init__(self):
        self.supabase = create_client(url, key)
    def getClient(self):
        return self.supabase

    async def lookup(self, link):
        db = self.getClient()
        return db.table("savedVideos").select("*").eq("link", link).execute()

    async def insert(self, link, file):
        if isinstance(file, list):
            await self.insertMediaGroup(link, file)
            return
        
        row = [link, file[0], file[1]]
        db = self.getClient()

        db.table("savedVideos").insert({
            "link": row[0],
            "file_id": [row[1]],
            "has_audio": [file[1]]
        }).execute()
        return
    
    async def insertMediaGroup(self, link, fileArray):
        db = self.getClient()

        db.table("savedVideos").insert({
            "link": link,
            "file_id": [file[0] for file in fileArray],
            "has_audio": [file[1] for file in fileArray]
        }).execute()