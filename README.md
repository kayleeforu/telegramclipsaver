<span align="center"><img src="https://img.shields.io/badge/Made%20with-Python-blue?style=flat&logo=python" alt="Python"> <img src="https://img.shields.io/badge/Made%20for-Telegram-26A5E0?style=flat&logo=telegram" alt="Telegram"> <img src="https://img.shields.io/badge/Database-Supabase-3ECF8E?style=flat&logo=supabase" alt="Supabase"> <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat" alt="Status"></span>

<h1 align="center"> Telegram Bot that downloads media from links</h1>
<p align="center">
  <img src="resources/botInline.gif" width="800">
</p>

This is my first big project that I built. Previously, I was only doing university works, but this is the bot that I can be proud of.

# Why use this bot?
I created this bot, because I was using other bots before to download posts that I couldn't download. However, I got annoyed by the amount of these bots that ask to subscribe to several channels or watch a literal video ad on Telegram in order to use the bot.

My bot doesn't ask you to do anything, you can simply send a link and get your video.

## Supported Platforms

| Platform  | Media Type              | Note (See Maintenance for cookies explanation) |
| --------- | ----------------------- | ---------------------------------------------- |
| TikTok    | Slideshow and Videos    | High speed                                     |
| Instagram | Posts and Reels         | High speed, but manual cookies update          |
| Pinterest | Photos, GIFs and Videos | High speed                                     |
| YouTube   | Videos and Shorts       | Low speed due to JS Challenges                 |

## APIs used
- The bot uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to download YouTube posts. 
- [Gallerydl](https://github.com/mikf/gallery-dl) for everything else.
- The bot also offers song recognition, if you download any video, you can press the button "Get Song" and the bot will try to recognize the song using [shazamio](https://github.com/shazamio/ShazamIO) and will send you the result.

## Optimization 
Supabase is used to cache the videos users queried, if someone else sends the same link, the bot will instantly send the result. This was made to speed up the process if the video was already downloaded before. The database doesn't store any video or path to it on the bot server. Telegram stores all its videos on their servers, and sends the bot the file id on their servers. Database stores the file id to the corresponding link and answers if the same link was queried.

### Maintenance
Because I didn't find any other solution to downloading posts on Instagram, I need to update cookies for instagram every now and then, but I notice bot not working pretty fast, so it doesn't take a lot of time to fix it. In order to ensure that the bot would work all the time, I would need more Instagram accounts and their cookies. That is why I sticked to just updating the cookies manually.