from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import ContextTypes
import re
from handlers.otherMessageHandling import otherMessage
from handlers.linkProcessing import processLink
from handlers.instagramProcessing import processInstagramPost
from utilities.deleteOriginalMessage import deleteOriginalMessage
from utilities.count import countAdd
import db
import logging
logger = logging.getLogger(__name__)

videoPost = [
    r"((https://)?v.\.tiktok\.com/\S*)",
    r"((https://(www\.)?)?tiktok.com/@(.*)/(\d{19})\?\S*)",
    r"((https://(www\.)?)?tiktok.com/\S*)",
    r"((https://(www\.)?)?youtube\.com/watch(\S*))",
    r"((https://(www\.)?)?youtu\.be/\S*)",
    r"((https://(www\.)?)?youtube\.com/shorts/\S*)",
    r"((https://(www\.)?)?instagram\.com/reel/\S*)",
    r"((https://(www\.)?)?pin\..{2}/\S*)",
    r"((https://(www\.)?)?pinterest\.com/pin/\S*)",
]
combinedVideos = "|".join(f"({p})" for p in videoPost)

instagramPost = r"((https://(www\.))?instagram\.com/p/(.{11})/\S*)"

database = db.database()

async def processMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message.text
    logger.info(f"message: {message}")
    videoPostLink = re.search(combinedVideos, message)
    instagramPostLink = re.search(instagramPost, message)
    logger.info(f"videoPostLink: {videoPostLink}")
    logger.info(f"instagramPostLink: {instagramPostLink}")
    logger.info(f"group 0: {videoPostLink.group(0)}")
    logger.info(f"group 1: {videoPostLink.group(1)}")
    if videoPostLink:
        link = videoPostLink.group(1)
        linkType = "video"
    elif instagramPostLink:
        link = instagramPostLink.group(1)
        linkType = "instagrampost"
    else:
        await otherMessage(update, context)
        return

    await getLinkAnswer(update, context, link, linkType)

async def databaseCheck(update: Update, context: ContextTypes.DEFAULT_TYPE, link, caption):
    response = await database.lookup(link)
    if response.data:
        row = response.data[0]
        file = (row["file_ids"][0], row["has_audio"][0])
        if file[1]:
                await context.bot.send_video(
                    chat_id = update.effective_chat.id,
                    video = file[0],
                    caption = caption
                )
        else:
                await context.bot.send_animation(
                    chat_id = update.effective_chat.id, 
                    animation = file[0],
                    caption = caption
                )
        await countAdd() # Downloaded Count + 1
    
        return True
    return False

async def databaseCheckMediaGroup(update: Update, context: ContextTypes.DEFAULT_TYPE, link, caption):
    response = await database.lookup(link)
    if response.data:
        media = []
        row = response.data[0]
        for file_id, has_audio in zip(row["file_ids"], row["has_audio"]):
            if has_audio:
                media.append(InputMediaVideo(file_id))
            else:
                media.append(InputMediaPhoto(file_id))

        await context.bot.send_media_group(
            chat_id = update.effective_chat.id,
            media = media,
            caption = caption
        )
        await countAdd() # Downloaded Count + 1

        return True
    return False

async def getLinkAnswer(update: Update, context: ContextTypes.DEFAULT_TYPE, link, linkType):
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    requestedBy = "@" + update.effective_sender.username if isGroupChat else None
    requestedMessage = update.effective_message.id if isGroupChat else None

    caption = f"Here is your video.\nRequested by: {requestedBy}\n\n@clip_saverbot"if isGroupChat \
                else "Here is your video.\n\n@clip_saverbot"

    if linkType == "video":
        if await databaseCheck(update, context, link, caption):
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            return
    elif linkType == "instagrampost":
        if await databaseCheckMediaGroup(update, context, link, caption):
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            return
    
    isMediaGroup = False
    if linkType == "video":
        result = await processLink(update, context, link)
    elif linkType == "instagrampost":
        result = await processInstagramPost(update, context, link)
        isMediaGroup = True
         
    if result and not isMediaGroup:
        await databaseCheck(update, context, link, caption)
        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
        return
    if result and isMediaGroup:
        await databaseCheckMediaGroup(update, context, link, caption)
        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
        return
    else:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Something went wrong :("
        )
        return