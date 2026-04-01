from telegram import Update, InputMediaVideo, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from telegram.error import RetryAfter
import asyncio
import re
from handlers.otherMessageHandling import otherMessage
from handlers.linkProcessing import processLink
from handlers.photosProcessing import processInstagramPost
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
    response = await database.lookUpLink(link)
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
    response = await database.lookUpLink(link)
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
            is_last = i + 10 >= len(media)
            try:
                await context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=chunk,
                    reply_to_message_id=repliesTo if i == 0 else None,
                    caption=caption if is_last else None,
                    parse_mode="MarkdownV2" if is_last else None
                )
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
                await context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=chunk,
                    reply_to_message_id=repliesTo if i == 0 else None,
                    caption=caption if is_last else None,
                    parse_mode="MarkdownV2" if is_last else None
                )

        await countAdd()
        return True
    return False

async def sendTypingWhileWorking(context, chat_id, stop_event, linkType):
    action = "upload_photo" if linkType == "instagrampost" else "upload_video"
    while not stop_event.is_set():
        await context.bot.send_chat_action(chat_id=chat_id, action=action)
        await asyncio.sleep(4)

async def getLinkAnswer(update: Update, context: ContextTypes.DEFAULT_TYPE, link, linkType):
    # Check if the link is already being processed
    response = await database.lookUpLink(link)
    if response.data and response.data[0]["file_ids"][0] == "processing":
        processing_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="The link is already being processed."
        )
        await asyncio.sleep(3)
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id
        )
        return

    # Set bot to typing to let user know that bot is working on their request
    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        sendTypingWhileWorking(context, update.effective_chat.id, stop_event, linkType)
    )
    await asyncio.sleep(0)

    # Add user to DB to see how many users use the bot
    user = update.effective_user
    if user is None:
        stop_event.set()
        await typing_task
        return
    userID = user.id

    response = await database.lookUpUser(userID)
    if not response.data:
        username = user.username or "NULL"
        await database.insertUser(userID, username)
    
    # Check if the message was requested in a group
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]

    escapedRequestedBy = ""
    hasUserName = False

    if isGroupChat:
        if update.effective_sender.username:
            requestedBy = "@" + update.effective_sender.username
            hasUserName = True
        else:
            requestedBy = f"{update.effective_sender.first_name}"
            hasUserName = False
        escapedRequestedBy = escape_markdown(requestedBy, version=2)
    else:
        requestedBy = None
    # Get user who requested the message and check their interface language
    requestedMessage = update.effective_message.id if isGroupChat else None
    isRussian = user and user.language_code == "ru"

    # Prepare caption depending on whether the chat is a group and if the interface language is Russian or not
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
    
    # April fools update
    linkMeme = "https://t.me/boost/operaofkaylee"
    escapedLinkMeme = escape_markdown(linkMeme, version=2)
    caption += f"\n\n[Мой бот в Макс]({escapedLinkMeme})"

    repliesTo = update.effective_message.reply_to_message.id if update.effective_message.reply_to_message else None

    try: 
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
            
        await database.insert(link, ("processing", False))

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
                chat_id=update.effective_chat.id,
                text="Something went wrong :(\n"
                    "Make sure your video is 60 min long or less"
            )
            return
    finally:
        stop_event.set()
        await typing_task