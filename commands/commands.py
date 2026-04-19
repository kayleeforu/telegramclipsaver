from telegram import Update
from telegram.ext import ContextTypes
from handlers.linkAnswer import getLinkAnswer
from utilities.shazamMusic import recognizeSong
import db
import logging
import os
import random

database = db.database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[start] args={context.args}")
    # isGroupChat = update.effective_chat.type in ["group", "supergroup"]
    # if isGroupChat:
    #     return
    
    if context.args:
        parameter = context.args[0]
                
        if parameter.startswith("download_"):
            key = parameter[len("download_"):]
            
            link = await database.getLinkByDeepKey(key)
            if not link:
                await update.message.reply_text(
                    text = "<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Invalid link.\n\n@clip_saverbot",
                    parse_mode = "HTML")
                return

            await getLinkAnswer(update, context, link, "instagrampost")
            return
        
        if parameter.startswith("getSong_"):
            key = parameter[len("getSong_"):]

            original_link = await database.getLinkByDeepKey(key)
            if not original_link:
                await update.message.reply_text(
                    text="<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Invalid link.",
                    parse_mode="HTML"
                )
                return 

            response = await database.lookUpLink(original_link)
            if not response.data:
                await update.message.reply_text(
                    text="<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Media data not found.",
                    parse_mode="HTML"
                )
                return
            
            link_data = response.data[0]

            audio_id = None
            if link_data.get('audioFile_ids') and len(link_data['audioFile_ids']) > 0:
                audio_id = link_data['audioFile_ids'][0]

            if not audio_id:
                await update.message.reply_text(
                    text="<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Can't extract audio from here.",
                    parse_mode="HTML"
                )
                return

            statusMessage = await update.message.reply_text(
                text="<tg-emoji emoji-id='5447282724886839705'>📂</tg-emoji> Processing audio...",
                parse_mode="HTML"
            )

            try:
                audioFile = await context.bot.get_file(audio_id)
                file_name = os.path.basename(audioFile.file_path)
                
                tempAudioPath = None
                search_root = "/var/lib/telegram-bot-api"
                
                for root, dirs, files in os.walk(search_root):
                    if file_name in files:
                        tempAudioPath = os.path.join(root, file_name)
                        break

                logging.info(f"Search for {file_name} in {search_root}. Result: {tempAudioPath}")

                if not tempAudioPath or not os.path.exists(tempAudioPath):
                    logging.error(f"File {file_name} NOT FOUND in {search_root}")
                    await statusMessage.edit_text(
                        "<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Something went wrong.",
                        parse_mode="HTML"
                    )
                    return

                await statusMessage.edit_text(
                    text="<tg-emoji emoji-id='5444883062234053429'>▶️</tg-emoji> Recognizing...",
                    parse_mode="HTML"
                )

                songResult = await recognizeSong(tempAudioPath)

                if songResult:
                    track = songResult['track']
                    title = track.get('title')
                    artist = track.get('subtitle')
                    url = track.get('url')
                    
                    text = f"<tg-emoji emoji-id='5445276884965291212'>🎧</tg-emoji> Found: <b>{artist} — {title}</b>"
                    if url:
                        text += f"\n\n<a href='{url}'>Listen on Shazam</a>"
                    
                    await statusMessage.edit_text(text, parse_mode="HTML", disable_web_page_preview=False)
                else:
                    await statusMessage.edit_text("<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Song not found.", parse_mode="HTML")

            except Exception as e:
                logging.error(f"Shazam Error: {e}")
                await statusMessage.edit_text("<tg-emoji emoji-id='5447647474984449520'>❌</tg-emoji> Something went wrong.", parse_mode="HTML")

            return

    user = update.effective_user
    russian = user and user.language_code == "ru"
    username = user.first_name

    if russian:
        text = "Приветствую, " + username + ". С помощью данного бота вы можете качать множество постов:\n" \
            "• ТикТок видео\n" \
            "• Инстаграм пост/рилс. Поддерживаются посты до 10 вложений.\n" \
            "• YouTube шортс\n" \
            "• YouTube видео до 60 минут\n" \
            "• Пинтерест видео/фотки\n\n" \
            "Чтобы скачать видео просто пришлите мне ссылку на него.\n" \
            "Вы так же можете использовать @clip_saverbot {ссылка} в любом другом чате, чтобы отправить пост через команду @\n\n" \
            "Спасибо за использование этого бота. Если хотите поддержать меня, напишите /support"
    else:
        text = "Welcome, " + username + ". You can download a variety of posts using this bot:\n" \
            "• TikTok video\n" \
            "• Instagram Post/Reels. Only posts up to 10 attachments are supported\n" \
            "• YouTube Shorts\n" \
            "• YouTube video up to 60 minutes\n" \
            "• Pinterest video/photos\n\n" \
            "To download a post just send me a link to it.\n" \
            "You can also use @clip_saverbot {link} in any other chat to send the post via the @ command.\n\n" \
            "Thank you for using this bot. If you want to support me, write /support"

    randomInt = random.randint(0, 100)
    if randomInt > 30:
        # video = "BAACAgQAAxkDAAIUnGnkBvaRNgrhaRvSKXqnryy1A0fCAALIGwAC4sQhU7FzvebEMzmEOgQ"
        video = "resources/botInline.mp4"
    else:
        # video = "BAACAgQAAxkDAAIUnmnkBwiREHJ3awL3ztwLvRV6hs0EAALJGwAC4sQhU8SApFC18oN5OgQ"
        video = "resources/botChat.mp4"

    message = await context.bot.send_video(
        chat_id = update.effective_chat.id,
        caption = text,
        video = video,
        supports_streaming = True
    )

    logging.info(message.video.file_id)

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
        photo = "AgACAgQAAxkDAAIQPWnc_O7Mt5qmg4CjhkFErpVwZvy0AALmDGsbCBbpUr-chN2YKunVAQADAgADeAADOgQ",
        caption = text
    )