import asyncio
import json
import os
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands, tasks

import radar

# Environment Variables untuk Channel IDs
NEWS_CHANNEL_ID = os.environ.get("DISCORD_NEWS_CHANNEL_ID", "")
ALERT_CHANNEL_ID = os.environ.get("DISCORD_ALERT_CHANNEL_ID", "")

# Path file persistensi untuk anti-spam news/listing
NEWS_MEMORY_FILE = "posted_news.json"
LISTING_MEMORY_FILE = "posted_listings.json"
MAX_MEMORY_ITEMS = 1000  # batasi growth supaya ga memory leak


def _load_set(path):
    """Load set dari JSON file (return empty set kalau belum ada / error)."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, json.JSONDecodeError):
        return set()


def _save_set(path, items):
    """Save set ke JSON file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(items), f)
    except OSError as e:
        print(f"[ERROR] Gagal simpan {path}: {e}")


class BackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Memory anti-spam yang persist di disk (survive restart)
        self.posted_news = _load_set(NEWS_MEMORY_FILE)
        self.posted_listings = _load_set(LISTING_MEMORY_FILE)

        # Mulai background loops
        self.news_radar.start()
        self.listing_radar.start()
        self.sniper_signal.start()

    def cog_unload(self):
        # Cancel tasks (fire-and-forget; bot is shutting down anyway)
        self.news_radar.cancel()
        self.listing_radar.cancel()
        self.sniper_signal.cancel()

    @tasks.loop(hours=1.0)
    async def news_radar(self):
        """Fetch 3 berita breaking dari CryptoCompare API setiap 1 jam"""
        await self.bot.wait_until_ready()

        if not NEWS_CHANNEL_ID:
            return

        channel = self.bot.get_channel(int(NEWS_CHANNEL_ID))
        if not channel:
            return

        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url) as resp,
            ):
                if resp.status != 200:
                    return
                data = await resp.json()
                results = data.get('Data', [])[:3]

                for item in reversed(results):
                    news_id = str(item['id'])
                    if news_id not in self.posted_news:
                        self.posted_news.add(news_id)

                        # Trim ke MAX_MEMORY_ITEMS termuda (pake deque biar efisien)
                        if len(self.posted_news) > MAX_MEMORY_ITEMS:
                            # Drop sembarang ~10% termuda? No — keep sembarang,
                            # karena set ga ordered. Untuk simplicity, biarkan
                            # set growing capped: buang arbitrary items.
                            to_remove = list(self.posted_news)[:len(self.posted_news) - MAX_MEMORY_ITEMS]
                            for r in to_remove:
                                self.posted_news.discard(r)

                        _save_set(NEWS_MEMORY_FILE, self.posted_news)

                        # Timezone-aware datetime (UTC)
                        pub_time = datetime.fromtimestamp(
                            item['published_on'], tz=timezone.utc
                        )

                        embed = discord.Embed(
                            title=item['title'],
                            url=item['url'],
                            color=discord.Color.orange(),
                            timestamp=pub_time
                        )

                        image_url = item.get('imageurl', '')
                        if image_url:
                            embed.set_thumbnail(url=image_url)

                        domain = item.get('source_info', {}).get('name', 'CryptoCompare')
                        embed.set_footer(text=f"Source: {domain}")

                        await channel.send(embed=embed)
        except Exception as e:
            print(f"[ERROR] News radar failed: {e}")

    @tasks.loop(minutes=5.0)
    async def listing_radar(self):
        """Pantau pengumuman dari Binance Announcement API setiap 5 menit"""
        await self.bot.wait_until_ready()

        if not ALERT_CHANNEL_ID:
            return

        channel = self.bot.get_channel(int(ALERT_CHANNEL_ID))
        if not channel:
            return

        url = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=5"

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url) as resp,
            ):
                if resp.status != 200:
                    return
                data = await resp.json()
                articles = data.get('data', {}).get('articles', [])

                for article in reversed(articles):
                    code = article['code']
                    title = article['title']

                    # Cek kata kunci listing di judul pengumuman
                    if ("List" in title or "Adds" in title) and code not in self.posted_listings:
                        self.posted_listings.add(code)

                        if len(self.posted_listings) > MAX_MEMORY_ITEMS:
                            to_remove = list(self.posted_listings)[:len(self.posted_listings) - MAX_MEMORY_ITEMS]
                            for r in to_remove:
                                self.posted_listings.discard(r)

                        _save_set(LISTING_MEMORY_FILE, self.posted_listings)

                        embed = discord.Embed(
                            title="🚨 NEW BINANCE LISTING DETECTED",
                            description=f"**{title}**\n\n[Read Official Announcement](https://www.binance.com/en/support/announcement/{code})",
                            color=discord.Color.gold()
                        )
                        await channel.send(embed=embed)
        except Exception as e:
            print(f"[ERROR] Listing radar failed: {e}")

    @tasks.loop(minutes=15.0)
    async def sniper_signal(self):
        """Loop untuk integrasi dengan radar.py (15 menit sekali)"""
        await self.bot.wait_until_ready()

        print("[INFO] Menjalankan Crypto Sniper Scanner di background thread...")
        try:
            # Karena radar.py berjalan secara synchronous, kita jalankan dengan asyncio.to_thread()
            # agar tidak memblokir event loop Discord bot
            await asyncio.to_thread(radar.run_scanner)
        except Exception as e:
            print(f"[ERROR] Sniper signal failed: {e}")


async def setup(bot):
    await bot.add_cog(BackgroundTasks(bot))
