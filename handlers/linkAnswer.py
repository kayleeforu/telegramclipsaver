from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
import re
from handlers.otherMessageHandling import otherMessage
from handlers.linkProcessing import processLink
from handlers.instagramProcessing import processInstagramPost
from utilities.deleteOriginalMessage import deleteOriginalMessage
from utilities.count import countAdd
import db

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
    videoPostLink = re.search(combinedVideos, message)
    instagramPostLink = re.search(instagramPost, message)
    if videoPostLink:
        link = videoPostLink.group(0)
        linkType = "video"
    elif instagramPostLink:
        link = instagramPostLink.group(0)
        linkType = "instagrampost"
    else:
        await otherMessage(update, context)
        return

    await getLinkAnswer(update, context, link, linkType)

async def databaseCheck(update: Update, context: ContextTypes.DEFAULT_TYPE, link, caption, repliesTo):
    response = await database.lookup(link)
    if response.data:
        row = response.data[0]
        if len(row["file_ids"]) > 1:
            return False
        file = (row["file_ids"][0], row["has_audio"][0])
        if file[1]:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=file[0],
                caption=caption,
                reply_to_message_id=repliesTo,
                parse_mode="MarkdownV2"
            )
        else:
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=file[0],
                caption=caption,
                reply_to_message_id=repliesTo,
                parse_mode="MarkdownV2"
            )
        await countAdd()
        return True
    return False

async def databaseCheckMediaGroup(update: Update, context: ContextTypes.DEFAULT_TYPE, link, caption, repliesTo):
    response = await database.lookup(link)
    if response.data:
        row = response.data[0]
        media = []
        for file_id, has_audio in zip(row["file_ids"], row["has_audio"]):
            if has_audio:
                media.append(InputMediaVideo(file_id))
            else:
                media.append(InputMediaPhoto(file_id))

        for i in range(0, len(media), 10):
            chunk = media[i:i+10]
            await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=chunk,
                reply_to_message_id=repliesTo if i == 0 else None,
            )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption,
            parse_mode="MarkdownV2"
        )

        await countAdd()
        return True
    return False

async def getLinkAnswer(update: Update, context: ContextTypes.DEFAULT_TYPE, link, linkType):
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    
    escapedRequestedBy = ""
    hasUserName = False
    
    if (isGroupChat):
        if (update.effective_sender.username):
            requestedBy = "@" + update.effective_sender.username
            hasUserName = True
        else:
            requestedBy = f"{update.effective_sender.first_name}"
            hasUserName = False

        escapedRequestedBy = escape_markdown(requestedBy, version=2)
    else: 
        requestedBy = None
    requestedMessage = update.effective_message.id if isGroupChat else None
    user = update.effective_user
    isRussian = user and user.language_code == "ru"

    if isRussian:
        if isGroupChat:
            if hasUserName:
                caption = f"Ваш пост\\.\nЗапрошено пользователем: {escapedRequestedBy}\n\n@clip\\_saverbot"
            else:
                caption = f"Ваш пост\\.\nЗапрошено пользователем: `{escapedRequestedBy}`\n\n@clip\\_saverbot"
        else:
            caption = f"Ваш пост\\.\n\n@clip\\_saverbot"
    else:
        if isGroupChat:
            if hasUserName:
                caption = f"Here is your post\\.\nRequested by: {escapedRequestedBy}\n\n@clip\\_saverbot"
            else:
                caption = f"Here is your post\\.\nRequested by: `{escapedRequestedBy}`\n\n@clip\\_saverbot"
        else:
            caption = f"Here is your post\\.\n\n@clip\\_saverbot"
    
    repliesTo = update.effective_message.reply_to_message.id if update.effective_message.reply_to_message else None

    if linkType == "video":
        if await databaseCheck(update, context, link, caption, repliesTo):
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            return
        if await databaseCheckMediaGroup(update, context, link, caption, repliesTo):
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            return
    elif linkType == "instagrampost":
        if await databaseCheckMediaGroup(update, context, link, caption, repliesTo):
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            return
    
    isMediaGroup = False
    if linkType == "video":
        result = await processLink(update, context, link)
    elif linkType == "instagrampost":
        result = await processInstagramPost(update, context, link)
        isMediaGroup = True
         
    if result == "slideshow":
        await databaseCheckMediaGroup(update, context, link, caption, repliesTo)
        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
        return
    elif result and not isMediaGroup:
        await databaseCheck(update, context, link, caption, repliesTo)
        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
        return
    elif result and isMediaGroup:
        await databaseCheckMediaGroup(update, context, link, caption, repliesTo)
        await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
        return
    else:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Something went wrong :(\n" \
            "Make sure your video is 60 min long or less"
        )
        return