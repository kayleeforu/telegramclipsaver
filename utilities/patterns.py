import re

videoPost = [
    r"((https://(www\.)?)?youtube\.com/watch(\S*))",
    r"((https://(www\.)?)?youtu\.be/\S*)",
    r"((https://(www\.)?)?youtube\.com/shorts/\S*)",
]
combinedVideos = "|".join(f"({p})" for p in videoPost)

galleryDl = [
    r"((https://(www\.))?instagram\.com/p/(.*)/\S*)",
    r"((https://(www\.)?)?instagram\.com/reel/\S*)",
    r"((https://(www\.)?)?pin\..{2}/\S*)",
    r"((https://(www\.)?)?pinterest\.com/pin/\S*)",
    r"((https://)?v.\.tiktok\.com/\S*)",
    r"((https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?\S*)",
    r"((https://(www\.)?)?tiktok.com/\S*)",
]
combinedGalleryDl = "|".join(f"({p})" for p in galleryDl)

def getLinkType(link):
    videoPostLink = re.search(combinedVideos, link)
    instagramPostLink = re.search(combinedGalleryDl, link)
    if videoPostLink:
        link = videoPostLink.group(0)
        linkType = "video"
    elif instagramPostLink:
        link = instagramPostLink.group(0)
        linkType = "galleryDl"
    return linkType, "tiktok" in link