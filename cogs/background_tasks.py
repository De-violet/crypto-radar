import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime
import asyncio
import radar

# Environment Variables untuk Channel IDs
NEWS_CHANNEL_ID = os.environ.get("DISCORD_NEWS_CHANNEL_ID", "")
ALERT_CHANNEL_ID = os.environ.get("DISCORD_ALERT_CHANNEL_ID", "")

class BackgroundTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Memory sederhana untuk mencegah spam berita/listing yang sama
        self.posted_news = set()
        self.posted_listings = set()
        
        # Mulai background loops
        self.news_radar.start()
        self.listing_radar.start()
        self.sniper_signal.start()

    def cog_unload(self):
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
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Ambil 3 berita teratas dari key 'Data'
                        results = data.get('Data', [])[:3]
                        
                        # Loop dengan reverse agar berita paling baru (index 0) dikirim terakhir (muncul paling bawah di Discord)
                        for item in reversed(results):
                            news_id = item['id']
                            if news_id not in self.posted_news:
                                self.posted_news.add(news_id)
                                
                                # Format waktu (unix timestamp)
                                pub_time = datetime.fromtimestamp(item['published_on'])
                                
                                embed = discord.Embed(
                                    title=item['title'],
                                    url=item['url'],
                                    color=discord.Color.orange(),
                                    timestamp=pub_time
                                )
                                
                                # Setup Thumbnail
                                image_url = item.get('imageurl', '')
                                if image_url:
                                    embed.set_thumbnail(url=image_url)
                                
                                # Setup Footer
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

        # Binance Announcement Public API URL (Un-official but commonly used)
        url = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=5"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get('data', {}).get('articles', [])
                        
                        for article in reversed(articles):
                            code = article['code']
                            title = article['title']
                            
                            # Cek kata kunci listing di judul pengumuman
                            if "List" in title or "Adds" in title:
                                if code not in self.posted_listings:
                                    self.posted_listings.add(code)
                                    
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
