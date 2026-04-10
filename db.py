from supabase import create_client
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

class database:
    def __init__(self):
        self.supabase = create_client(url, key)
    def getClient(self):
        return self.supabase

    async def lookUpLink(self, link):
        db = self.getClient()
        return db.table("savedVideos").select("*").eq("link", link).execute()

    async def insert(self, link, file):
        if isinstance(file, list):
            await self.insertMediaGroup(link, file)
            return
        
        videoID = file[0]
        hasAudio = file[1]
        audioID = file[2] if len(file) > 2 else None
        
        db = self.getClient()

        db.table("savedVideos").upsert({
            "link": link,
            "file_ids": [videoID],
            "has_audio": [hasAudio],
            "audioFile_ids": [audioID]
        }).execute()
    
    async def insertMediaGroup(self, link, fileArray):
        db = self.getClient()
        db.table("savedVideos").upsert({
            "link": link,
            "file_ids": [file[0] for file in fileArray],
            "has_audio": [file[1] for file in fileArray]
        }).execute()

    async def lookUpUser(self, userID):
        db = self.getClient()

        return db.table("users").select("*").eq("id", int(userID)).execute()

    async def insertUser(self, userID, username, firstName):
        db = self.getClient()

        db.table("users").upsert({
            "id": int(userID),
            "username": username,
            "firstName": firstName
        }).execute()

    async def removeLink(self, link):
        db = self.getClient()

        db.table("savedVideos").delete().eq("link", link).execute()

    async def insertDeepLink(self, key, link):
        db = self.getClient()
        db.table("deeplinks").upsert({
            "key": key,
            "link": link
        }).execute()

    async def getLinkByDeepKey(self, key):
        db = self.getClient()
        result = db.table("deeplinks").select("*").eq("key", key).execute()
        if result.data:
            return result.data[0]["link"]
        return None

    async def removeDeepLink(self, key):
        db = self.getClient()
        db.table("deeplinks").delete().eq("key", key).execute()

    async def addCount(self, userID: int):
        db = self.getClient()
        response = db.table("users").select("count").eq("id", userID).execute()
        count = 0
        if response.data:
            count = int(response.data[0]["count"])
        db.table("users").upsert({
            "id": userID,
            "count": count + 1
        }).execute()