import os
import sys
from keep_alive import keep_alive
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════
# DISCORD BOT SETUP (Crypto Command Center)
# ══════════════════════════════════════════════

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
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} slash commands berhasil disinkronisasi!")
        except Exception as e:
            print(f"❌ Gagal sync slash commands: {e}")


bot = CryptoBot()


@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'📡 News channel : {os.environ.get("DISCORD_NEWS_CHANNEL_ID", "(not set)")}')
    print(f'🚨 Alert channel: {os.environ.get("DISCORD_ALERT_CHANNEL_ID", "(not set)")}')
    print('------')


if __name__ == '__main__':
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

    if not DISCORD_TOKEN:
        print("❌ FATAL: Environment variable DISCORD_TOKEN tidak ditemukan.")
        print("   Set dulu sebelum run:")
        print("   - Windows : $env:DISCORD_TOKEN=\"token_kamu\"")
        print("   - Linux/Mac: export DISCORD_TOKEN=\"token_kamu\"")
        print("   - Atau masukkan ke .env file (lihat .env.example)")
        sys.exit(1)

    # Start keep-alive HTTP server (for platforms like HF Spaces / Render / Replit)
    keep_alive()

    # Run Discord bot
    bot.run(DISCORD_TOKEN)
