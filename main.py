"""
Crypto Radar v7.0 — Discord Bot entry point.

Refactored: can be imported as a module (FastAPI main akan import `bot` untuk
jalan bersamaan di 1 container). Tetap bisa dijalankan langsung `python main.py`.

Usage:
    python main.py                # standalone Discord bot + keep_alive HTTP server
    # atau import dari apps/api/main.py untuk coexist dengan FastAPI
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Pastikan cwd ada di sys.path supaya `import radar`, `from cogs...` jalan
# terlepas dari direktori apa yang dipakai jalan `python main.py`.
sys.path.insert(0, str(Path(__file__).parent.resolve()))

load_dotenv()


def create_bot() -> commands.Bot:
    """Factory: bikin instance Discord bot. Bisa dipanggil ulang dari FastAPI."""

    intents = discord.Intents.default()
    intents.message_content = True

    class CryptoBot(commands.Bot):
        def __init__(self):
            super().__init__(
                command_prefix="!",
                intents=intents,
                help_command=None,
            )

        async def setup_hook(self):
            cogs_dir = Path(__file__).parent / "cogs"
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    await self.load_extension(f"cogs.{filename[:-3]}")

            try:
                synced = await self.tree.sync()
                print(f"✅ {len(synced)} slash commands berhasil disinkronisasi!")
            except Exception as e:
                print(f"❌ Gagal sync slash commands: {e}")

    return CryptoBot()


# Singleton bot instance (di-import oleh FastAPI kalau jalan di 1 container)
bot = create_bot()


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"📡 News channel : {os.environ.get('DISCORD_NEWS_CHANNEL_ID', '(not set)')}")
    print(f"🚨 Alert channel: {os.environ.get('DISCORD_ALERT_CHANNEL_ID', '(not set)')}")
    print("------")


def run_standalone():
    """Jalan standalone: keep-alive HTTP + Discord bot di 1 proses."""
    from keep_alive import keep_alive  # lazy import supaya FastAPI mode tidak wajib Flask

    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
    if not DISCORD_TOKEN:
        print("❌ FATAL: Environment variable DISCORD_TOKEN tidak ditemukan.")
        print("   Set dulu sebelum run:")
        print("   - Linux/Mac : export DISCORD_TOKEN=\"token_kamu\"")
        print("   - Windows   : $env:DISCORD_TOKEN=\"token_kamu\"")
        print("   - Atau masukkan ke .env file (lihat .env.example)")
        sys.exit(1)

    keep_alive()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run_standalone()
