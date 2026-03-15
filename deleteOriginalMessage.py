from telegram import Update
from telegram.ext import ContextTypes
import asyncio

async def deleteOriginalMessage(update, context, requestedMessage, requestedBy):
    if requestedBy is not None:
                try:
                    await context.bot.delete_message(update.effective_chat.id, requestedMessage)
                except:
                    unableToDeleteMessage = await context.bot.send_message(update.effective_chat.id, text = "I can't delete the original message with a link.\n" \
                    "If you want me to delete them, give me the right to delete the messages." + update.effective_message.text)
                    await asyncio.sleep(5)
                    await context.bot.delete_message(update.effective_chat.id, unableToDeleteMessage.message_id)