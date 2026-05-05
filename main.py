import os
from keep_alive import keep_alive
import discord
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

# ══════════════════════════════════════════════
# DISCORD BOT SETUP (Crypto Command Center)
# ══════════════════════════════════════════════

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True  # Dibutuhkan untuk membaca pesan

class CryptoBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!', 
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Load semua Cogs secara dinamis
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        
        # Sinkronisasi Slash Commands ke Discord API
        await self.tree.sync()
        print("✅ Slash commands berhasil disinkronisasi!")

bot = CryptoBot()

@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

if __name__ == '__main__':
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_DISCORD_TOKEN_HERE")
    
    if DISCORD_TOKEN == "YOUR_DISCORD_TOKEN_HERE":
        print("⚠️ Mohon set environment variable DISCORD_TOKEN terlebih dahulu.")
        print("Contoh Windows: $env:DISCORD_TOKEN=\"token_kamu_di_sini\"")
        print("Contoh Linux/Mac: export DISCORD_TOKEN=\"token_kamu_di_sini\"")
    else:
        bot.run(DISCORD_TOKEN)
