from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    if isGroupChat:
        return

    user = update.effective_user
    russian = user and user.language_code == "ru"
    username = user.first_name

    if russian:
        text = "Приветствую, " + username + ". С помощью данного бота вы можете качать множество постов:\n" \
            "• ТикТок видео\n" \
            "• Инстаграм пост/рилс. Поддерживаются посты до 10 вложений.\n" \
            "• YouTube шортс\n" \
            "• YouTube видео до 10 минут (Будет меняться в будущем)\n\n" \
            "Вы так же можете использовать @clip_saverbot {ссылка} в любом другом чате, чтобы отправить пост через команду @\n\n" \
            "Спасибо за использование этого бота. Если хотите поддержать меня, напишите /support"
    else:
        text = "Welcome, " + username + ". You can download a variety of posts using this bot:\n" \
            "• TikTok video\n" \
            "• Instagram Post/Reels. Only posts up to 10 attachments are supported\n" \
            "• YouTube Shorts\n" \
            "• YouTube video up to 10 minutes (Will be changed in the future)\n\n" \
            "You can also use @clip_saverbot {link} in any other chat to send the post via the @ command.\n" \
            "Thank you for using this bot. If you want to support me, write /support"

    await context.bot.send_message(
        chat_id = update.effective_chat.id,
        text = text
    )