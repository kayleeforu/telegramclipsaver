from telegram import Update
from telegram.ext import ContextTypes
from handlers.linkAnswer import getLinkAnswer
from handlers.inlinePostProcessing import pending  
import logging


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[start] args={context.args}")
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    if isGroupChat:
        return
    
    if context.args:
        parameter = context.args[0]

        if parameter.startswith("download_"):
            key = parameter[len("download_"):]
            
            link = pending.pop(key, None)

            if not link:
                await update.message.reply_text("❌ This link expired or is invalid.")
                return

            await getLinkAnswer(update, context, link, "instagrampost")
            return

    user = update.effective_user
    russian = user and user.language_code == "ru"
    username = user.first_name

    if russian:
        text = "Приветствую, " + username + ". С помощью данного бота вы можете качать множество постов:\n" \
            "• ТикТок видео\n" \
            "• Инстаграм пост/рилс. Поддерживаются посты до 10 вложений.\n" \
            "• YouTube шортс\n" \
            "• YouTube видео до 60 минут\n\n" \
            "Чтобы скачать видео просто пришлите мне ссылку на него." \
            "Вы так же можете использовать @clip_saverbot {ссылка} в любом другом чате, чтобы отправить пост через команду @\n\n" \
            "Спасибо за использование этого бота. Если хотите поддержать меня, напишите /support"
    else:
        text = "Welcome, " + username + ". You can download a variety of posts using this bot:\n" \
            "• TikTok video\n" \
            "• Instagram Post/Reels. Only posts up to 10 attachments are supported\n" \
            "• YouTube Shorts\n" \
            "• YouTube video up to 60 minutes\n\n" \
            "To download a post just send me a link to it." \
            "You can also use @clip_saverbot {link} in any other chat to send the post via the @ command.\n" \
            "Thank you for using this bot. If you want to support me, write /support"

    await context.bot.send_message(
        chat_id = update.effective_chat.id,
        text = text
    )


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    if isGroupChat:
        return
    
    user = update.effective_user
    isRussian = user.language_code == "ru"
    name = user.first_name

    if isRussian:
        text = f"Привет, {name}. Ты можешь меня поддержать, купив мне кофе: ko-fi.com/kayleeforu, я буду очень вам благодарна!\n\n" \
        "Для связи со мной можешь написать мне в личные сообщения: @kayleeforu"
    else:
        text = f"Hey, {name}. You can support me by buying me a coffee at: ko-fi.com/kayleeforu, I will be really grateful!\n\n" \
        "If you want to contact me, write me in direct messages: @kayleeforu"

    await context.bot.send_photo(
        chat_id = update.effective_chat.id,
        photo = "resources/supportPic.jpg",
        caption = text
    )