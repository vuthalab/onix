# import simplematrixbotlib as botlib

# creds = botlib.Creds("https://matrix.org", "onix_bot", "153euyso3+")
# bot = botlib.Bot(creds)
# config = botlib.Config()
# config.encryption_enabled = True
# config.ignore_unverified_devices = False
# PREFIX = '!'
# room = "test_bot"

# @bot.listener.on_message_event
# async def echo(room, message):
#     match = botlib.MessageMatch(room, message, bot, PREFIX)

#     if match.is_not_from_this_bot() and match.prefix() and match.command("echo"):

#         await bot.api.send_text_message(
#             room.room_id, " ".join(arg for arg in match.args())
#             )

# bot.run()

import simplematrixbotlib as botlib

config = botlib.Config()
config.encryption_enabled = True
config.ignore_unverified_devices = False
config.store_path = './crypto_store/'
config.emoji_verify = True
creds = botlib.Creds("https://matrix.org", "onix_bot", "153euyso3+")
bot = botlib.Bot(creds, config)
PREFIX = '!'
room = "test_bot"

@bot.listener.on_message_event
async def echo(room, message):
    match = botlib.MessageMatch(room, message, bot, PREFIX)

    if match.is_not_from_this_bot()\
            and match.prefix()\
            and match.command("echo"):

        await bot.api.send_text_message(room.room_id,
                                        " ".join(arg for arg in match.args()))


bot.run()