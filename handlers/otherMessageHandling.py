from telegram import Update
from telegram.ext import ContextTypes
import re

async def otherMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    if isGroupChat: 
        return

    user = update.effective_user
    russian = user and user.language_code == "ru"

    message = update.message.text if update.message and update.message.text else ""
    isLink = bool(re.search(r"https?://\S+|www\.\S+", message))

    if not isLink and len(message) < 3:
        return

    if isLink:
        if russian:
            text = "Простите, но пока что я не поддерживаю данный тип постов.\n" \
                "Вы можете отправить мне:\n" \
                "• ТикТок видео\n" \
                "• Инстаграм пост/рилс. Поддерживаются посты до 10 вложений.\n" \
                "• YouTube шортс\n" \
                "• YouTube видео до 40 минут\n\n" \
                "Помните, вы можете использовать @clip_saverbot {ссылка} в любом другом чате, чтобы отправить пост через команду @\n\n" \
                "Спасибо за использование этого бота."
        else:
            text = "Sorry, I don't support this type of posts.\n" \
                "You can send me:\n" \
                "• TikTok video\n" \
                "• Instagram Post/Reels. Only posts up to 10 attachments are supported\n" \
                "• YouTube Shorts\n" \
                "• YouTube video up to 40 minutes\n\n" \
                "Remember, you can use @clip_saverbot {link} in any other chat to send the post via the @ command.\n" \
                "Thank you for using this bot."
    else:
        if russian:
            text = "Для того, чтобы скачать пост, отправьте ссылку чат.\n\n" \
                "Другой способ скачать пост - это использовать\n@clip_saverbot {ссылка} в любом другом чате.\n" \
                "Скачивание YouTube видео (не Shorts) не рекомендуется, потому что требует больше времени.\n\n" \
                "Спасибо за использование этого бота."
        else:
            text = "To download a post, send me a link in this chat.\n\n" \
                "Another way to download the post is to use:\n@clip_saverbot {link} in any other chat.\n" \
                "However, it is not recommended to download YouTube videos (not Shorts), because of the larger video size.\n\n" \
                "Thank you for using this bot."

    await context.bot.send_message(
        chat_id = update.effective_chat.id,
        text = text
    )