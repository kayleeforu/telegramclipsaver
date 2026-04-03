from telegram import Update, InlineQueryResultCachedVideo, InlineQueryResultCachedMpeg4Gif, InlineQueryResultArticle, InputTextMessageContent, InputMediaVideo, InputMediaAnimation, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultCachedPhoto
from telegram.ext import ContextTypes
from utilities.savevid import downloadVideo
from utilities.patterns import getLinkType
from handlers.photosProcessing import processTikTokSlideshow, processInstagramPost
from utilities.cacheVideo import uploadToChannel
import uuid
import subprocess
import db
import asyncio
import logging

clearVids = "rm -f downloadedVideos/*"
database = db.database()
pending = {}


async def checkDatabase(update: Update, context: ContextTypes.DEFAULT_TYPE, link):
    response = (await database.lookUpLink(link)).data
    if response:
        file = (response[0]["file_ids"][0], response[0]["has_audio"][0])
        if file[0] == "processing":
            inlineID = InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="⏳ Already processing...",
                input_message_content=InputTextMessageContent("⏳ Downloading the post...")
            )
            await context.bot.answer_inline_query(
                inline_query_id=update.inline_query.id,
                results=[inlineID],
                cache_time=0
            )
            return False
        elif file[1]:
            inlineID = InlineQueryResultCachedVideo(
                id=str(uuid.uuid4()),
                video_file_id=file[0],
                title="Video",
                caption="🎬 Downloaded via @clip_saverbot"
            )
        else:
            if file[0].startswith("AgAC"):
                key = str(uuid.uuid4())[:8]
                pending[key] = link
                deepLink = f"https://t.me/clip_saverbot?start=download_{key}"

                inlineID = InlineQueryResultCachedPhoto(
                    id=str(uuid.uuid4()),
                    photo_file_id=file[0],
                    title="Photo",
                    caption=f'🌅 Here is one photo:\n<a href="{deepLink}">Click to view the full post</a>\n\n@clip_saverbot',
                    parse_mode="HTML"
                )
            else:
                inlineID = InlineQueryResultCachedMpeg4Gif(
                    id=str(uuid.uuid4()),
                    mpeg4_file_id=file[0],
                    title="GIF",
                    caption="🎬 Downloaded via @clip_saverbot"
                )

        await context.bot.answer_inline_query(
            inline_query_id=update.inline_query.id,
            results=[inlineID],
            cache_time=0
        )
        return True
    return False


async def processPostInline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.inline_query.query
    if not link:
        return

    if (await checkDatabase(update, context, link)):
        return

    resultID = str(uuid.uuid4())
    pending[resultID] = link

    inlineID = InlineQueryResultArticle(
        id=resultID,
        title="🏷 Click to download a post",
        input_message_content=InputTextMessageContent(message_text="⏳ Downloading the post..."),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ Processing...", callback_data="processing")]
        ])
    )

    await context.bot.answer_inline_query(
        inline_query_id=update.inline_query.id,
        results=[inlineID],
        cache_time=0
    )


async def chosenInlineResult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resultID = update.chosen_inline_result.result_id
    inlineMessageID = update.chosen_inline_result.inline_message_id
    link = update.chosen_inline_result.query

    if not inlineMessageID:
        logging.warning(f"[chosenInlineResult] No inline_message_id for result {resultID}")
        return

    if not pending.get(resultID):
        return
    else:
        pending.pop(resultID)

    await database.insert(link, ("processing", False))

    asyncio.create_task(
        processAndEdit(context, inlineMessageID, link)
    )


async def processAndEdit(context, inlineMessageID, link):
    try:
        linkType, isTiktok = getLinkType(link)

        key = str(uuid.uuid4())[:8]
        pending[key] = link
        deepLink = f"https://t.me/clip_saverbot?start=download_{key}"

        loop = asyncio.get_running_loop()

        if linkType == "video":
            filepath, hasAudio, thumbnailpath, height, width = await loop.run_in_executor(
                None, lambda: downloadVideo(link)
            )

            if filepath is None:
                subprocess.run(clearVids, shell=True)

                if isTiktok:
                    await processTikTokSlideshow(context, link)
                    response = (await database.lookUpLink(link)).data
                    if response:
                        file_id = response[0]["file_ids"][0]
                        await context.bot.edit_message_media(
                            inline_message_id=inlineMessageID,
                            media=InputMediaPhoto(
                                file_id,
                                caption=f'🌅 Here is one photo:\n<a href="{deepLink}">Click to view the full post</a>\n\n@clip_saverbot',
                                parse_mode="HTML"
                            )
                        )
                    else:
                        await context.bot.edit_message_text(
                            inline_message_id=inlineMessageID,
                            text="❌ Failed to download the post.\n\n@clip_saverbot"
                        )
                        await database.removeLink(link)
                    return
                else:
                    await context.bot.edit_message_text(
                        inline_message_id=inlineMessageID,
                        text="❌ Failed to download the video.\n\n@clip_saverbot"
                    )
                    await database.removeLink(link)
                    return

            result = await uploadToChannel(context, filepath, hasAudio, thumbnailpath, height, width, link)

            if result is None:
                await context.bot.edit_message_text(
                    inline_message_id=inlineMessageID,
                    text="❌ Failed to download the video.\n\n@clip_saverbot"
                )
                subprocess.run(clearVids, shell=True)
                await database.removeLink(link)
                return
            else:
                await database.insert(link, result)

            await context.bot.edit_message_media(
                inline_message_id=inlineMessageID,
                media=InputMediaVideo(result[0], caption="🎬 Downloaded via @clip_saverbot")
                if result[1]
                else InputMediaAnimation(result[0], caption="🎬 Downloaded via @clip_saverbot")
            )

        elif linkType == "instagrampost":
            await processInstagramPost(context, link)
            response = (await database.lookUpLink(link)).data
            if response:
                file_id = response[0]["file_ids"][0]
                await context.bot.edit_message_media(
                    inline_message_id=inlineMessageID,
                    media=InputMediaPhoto(
                        file_id,
                        caption=f'🌅 Here is one photo:\n<a href="{deepLink}">Click to view the full post</a>\n\n@clip_saverbot',
                        parse_mode="HTML"
                    )
                )
            else:
                await context.bot.edit_message_text(
                    inline_message_id=inlineMessageID,
                    text="❌ Failed to download the video.\n\n@clip_saverbot"
                )
                await database.removeLink(link)
            return

    except Exception as e:
        logging.error(f"[processAndEdit] Unexpected error: {e}")
        try:
            await context.bot.edit_message_text(
                inline_message_id=inlineMessageID,
                text="❌ Something went wrong.\n\n@clip_saverbot"
            )
        except Exception:
            pass
        await database.removeLink(link)