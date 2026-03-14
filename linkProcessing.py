from telegram import Update
from telegram.ext import ContextTypes
from savevid import downloadVideo
from count import countAdd
import subprocess
import asyncio
from database import supabase

async def processLink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    requestedBy = "@" + update.effective_sender.username if isGroupChat else None
    requestedMessage = update.effective_message.id if isGroupChat else None

    (filepath, hasAudio) = downloadVideo(link)
    if filepath is None:
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "Unknown issue."
        )
        return
    elif filepath == "too_long":
        await context.bot.send_message(
            chat_id = update.effective_chat.id,
            text = "The video is too long.\nTry a video that is shorter than 10 minutes."
        )
        return
    
    try:
        with open(filepath, "rb") as f:
            caption = f"Here is your video.\nRequested by: {requestedBy}\n\n@clip_saverbot"if isGroupChat \
                else "Here is your video.\n\n@clip_saverbot"
            if hasAudio:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=f,
                    caption=caption,
                    supports_streaming=True
                )
            else:
                await context.bot.send_animation(
                    chat_id=update.effective_chat.id,
                    animation=f,
                    caption=caption,
                )
            await deleteOriginalMessage(update, context, requestedMessage, requestedBy)

    finally:
        subprocess.run(["rm", "/downloadedVideos/*"])

    await countAdd()

async def deleteOriginalMessage(update, context, requestedMessage, requestedBy):
    if requestedBy is not None:
                try:
                    await context.bot.delete_message(update.effective_chat.id, requestedMessage)
                except:
                    unableToDeleteMessage = await context.bot.send_message(update.effective_chat.id, text = "I can't delete the original message with a link.\n" \
                    "If you want me to delete them, give me the right to delete the messages.")
                    await asyncio.sleep(5)
                    await context.bot.delete_message(update.effective_chat.id, unableToDeleteMessage.message_id)