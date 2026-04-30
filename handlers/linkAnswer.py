from telegram import Update, InputMediaVideo, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import RetryAfter
import asyncio
import re
from handlers.otherMessageHandling import otherMessage, instagramTempDisabled
from handlers.linkProcessing import processLink
from handlers.photosProcessing import processInstagramPost
from utilities.deleteOriginalMessage import deleteOriginalMessage
import db
import uuid
import utilities.patterns as patterns
import logging

database = db.database()

async def processMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message.text
    logging.info(f"[processMessage] message: {message}")
    videoPostLink = re.search(patterns.combinedVideos, message)
    galleryDlLink = re.search(patterns.combinedGalleryDl, message)
    instagramLink = re.search(r"((https://(www\.))?instagram\.com/p/(.*)/\S*)|((https://(www\.)?)?instagram\.com/reel/\S*)", message)
    if videoPostLink:
        link = videoPostLink.group(0)
        linkType = "video"
    elif galleryDlLink:
        link = galleryDlLink.group(0)
        linkType = "galleryDl"
    elif instagramLink:
        await instagramTempDisabled(update, context)
        return
    else:
        await otherMessage(update, context)
        return

    await getLinkAnswer(update, context, link, linkType)

async def databaseCheck(update: Update, context: ContextTypes.DEFAULT_TYPE, link, caption, repliesTo):
    response = await database.lookUpLink(link)
    if response.data:
        key = str(uuid.uuid4())[:8]
        await database.insertDeepLink(key, link)
        deepLinkSong = f"https://t.me/clip_saverbot?start=getSong_{key}"
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
                parse_mode="HTML",
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="🎧 Get Song", url=deepLinkSong)]
                ])
            )
        else:
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=file[0],
                caption=caption,
                reply_to_message_id=repliesTo,
                parse_mode="HTML"
            )
        return True
    return False

async def databaseCheckMediaGroup(update: Update, context: ContextTypes.DEFAULT_TYPE, link, caption, repliesTo):
    response = await database.lookUpLink(link)
    if response.data:
        row = response.data[0]
        
        key = str(uuid.uuid4())[:8]
        await database.insertDeepLink(key, link)
        deepLinkSong = f"https://t.me/clip_saverbot?start=getSong_{key}"

        if len(row["file_ids"]) == 1:
            file_id = row["file_ids"][0]
            has_audio = row["has_audio"][0]
            if str(file_id).startswith("AgAC"):
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                    caption=caption,
                    reply_to_message_id=repliesTo,
                    parse_mode="HTML"
                )
            else:
                if has_audio:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=file_id,
                        caption=caption,
                        reply_to_message_id=repliesTo,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🎧 Get Song", url=deepLinkSong)]])
                    )
                else:
                    await context.bot.send_animation(
                        chat_id=update.effective_chat.id,
                        animation=file_id,
                        caption=caption,
                        reply_to_message_id=repliesTo,
                        parse_mode="HTML"
                    )
            return True

        media = []
        for file_id, has_audio, audio_id in zip(row["file_ids"], row["has_audio"], row["audioFile_ids"]):
            if str(file_id).startswith("AgAC"):
                media.append(InputMediaPhoto(file_id))
            else:
                media.append(InputMediaVideo(file_id))

        for i in range(0, len(media), 10):
            chunk = media[i:i+10]
            is_last = i + 10 >= len(media)
            
            final_caption = caption
            if is_last and any(row["has_audio"]):
                final_caption += f'\n\n<a href="{deepLinkSong}">🎧 Get Song</a>'

            try:
                await context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=chunk,
                    reply_to_message_id=repliesTo if i == 0 else None,
                    caption=final_caption if is_last else None,
                    parse_mode="HTML" if is_last else None
                )
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
                await context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=chunk,
                    reply_to_message_id=repliesTo if i == 0 else None,
                    caption=final_caption if is_last else None,
                    parse_mode="HTML" if is_last else None
                )

        return True
    return False

async def sendTypingWhileWorking(context, chat_id, stop_event, linkType):
    action = "upload_video"
    while not stop_event.is_set():
        await context.bot.send_chat_action(chat_id=chat_id, action=action)
        await asyncio.sleep(4)

async def getLinkAnswer(update: Update, context: ContextTypes.DEFAULT_TYPE, link, linkType):
    inserted = await database.insertProcessingIfNotExists(link)

    if not inserted:
        response = await database.lookUpLink(link)
        if response.data and response.data[0]["file_ids"][0] == "processing":
            processing_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="<tg-emoji emoji-id='5447389837076231920'>⏳</tg-emoji> The link is already being processed.",
                parse_mode="HTML",
            )
            await asyncio.sleep(5)
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )
            return

    user = update.effective_user
    if user is None:
        await database.removeLink(link)
        return
    userID = user.id

    response = await database.lookUpUser(userID)
    if not response.data or not response.data[0]["firstName"]:
        username = user.username or None
        await database.insertUser(userID, username, user.first_name)

    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    hasUserName = False
    if isGroupChat:
        if update.effective_sender.username:
            requestedBy = "@" + update.effective_sender.username
            hasUserName = True
        else:
            requestedBy = update.effective_sender.first_name
            hasUserName = False
    else:
        requestedBy = None

    requestedMessage = update.effective_message.id if isGroupChat else None
    isRussian = user and user.language_code == "ru"

    caption = "<tg-emoji emoji-id='5447471097857473538'>📎</tg-emoji> "
    if isRussian:
        if isGroupChat:
            if hasUserName:
                caption += f"Ваш пост.\nЗапрошено пользователем: {requestedBy}"
            else:
                caption += f"Ваш пост.\nЗапрошено пользователем: <code>{requestedBy}</code>"
        else:
            caption += "Ваш пост."
    else:
        if isGroupChat:
            if hasUserName:
                caption += f"Here is your post.\nRequested by: {requestedBy}"
            else:
                caption += f"Here is your post.\nRequested by: <code>{requestedBy}</code>"
        else:
            caption += "Here is your post."
    caption += f"\n\n@clip_saverbot"

    repliesTo = update.effective_message.reply_to_message.id if update.effective_message.reply_to_message else None

    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(
        sendTypingWhileWorking(context, update.effective_chat.id, stop_event, linkType)
    )
    await asyncio.sleep(0)

    try:
        if not inserted:
            if linkType == "video":
                if await databaseCheck(update, context, link, caption, repliesTo):
                    await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
                    await database.addCount(userID)
                    return
                if await databaseCheckMediaGroup(update, context, link, caption, repliesTo):
                    await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
                    await database.addCount(userID)
                    return
            elif linkType == "galleryDl":
                if await databaseCheckMediaGroup(update, context, link, caption, repliesTo):
                    await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
                    await database.addCount(userID)
                    return
            return

        isMediaGroup = False
        if linkType == "video":
            result = await processLink(update, context, link)
            if result is None:
                await database.removeLink(link)
                return
        elif linkType == "galleryDl":
            result = await processInstagramPost(context, link)
            isMediaGroup = True

        if result == "slideshow":
            await databaseCheckMediaGroup(update, context, link, caption, repliesTo)
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            await database.addCount(userID)
        elif result and not isMediaGroup:
            await databaseCheck(update, context, link, caption, repliesTo)
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            await database.addCount(userID)
        elif result and isMediaGroup:
            await databaseCheckMediaGroup(update, context, link, caption, repliesTo)
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)
            await database.addCount(userID)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Something went wrong :(\nMake sure your video is 60 min long or less",
                parse_mode="HTML"
            )
            await database.removeLink(link)
    finally:
        stop_event.set()
        await typing_task