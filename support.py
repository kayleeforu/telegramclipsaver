from telegram import Update
from telegram.ext import ContextTypes

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