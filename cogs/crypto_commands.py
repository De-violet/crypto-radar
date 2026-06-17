import time
from collections import OrderedDict

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Simple TTL cache (LRU + expiry). Avoid external deps.
_CACHE_TTL = 60  # 60 detik
_cache: OrderedDict = OrderedDict()
_CACHE_MAX = 100


def _cache_get(key):
    if key in _cache:
        value, expires_at = _cache[key]
        if time.time() < expires_at:
            _cache.move_to_end(key)
            return value
        del _cache[key]
    return None


def _cache_set(key, value):
    _cache[key] = (value, time.time() + _CACHE_TTL)
    _cache.move_to_end(key)
    if len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


class CryptoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="search", description="Fetch harga real-time, Market Cap, 24h change, dan Rank.")
    @app_commands.describe(coin="Coin ID di CoinGecko (contoh: bitcoin, ethereum, solana)")
    async def search(self, interaction: discord.Interaction, coin: str):
        await interaction.response.defer()

        coin_id = coin.lower().replace(" ", "-")

        # Cek cache dulu
        cached = _cache_get(f"search:{coin_id}")
        if cached:
            data = cached
        else:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"

            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response,
                ):
                    if response.status == 429:
                        await interaction.followup.send(
                            "⏳ CoinGecko rate limit tercapai. Coba lagi dalam 1 menit."
                        )
                        return
                    if response.status != 200:
                        await interaction.followup.send(
                            f"❌ Koin `{coin}` tidak ditemukan (HTTP {response.status})."
                        )
                        return
                    data = await response.json()
                    _cache_set(f"search:{coin_id}", data)
            except aiohttp.ClientError as e:
                await interaction.followup.send(f"❌ Network error: `{e}`")
                return

        market_data = data.get('market_data', {})
        price = market_data.get('current_price', {}).get('usd', 0)
        market_cap = market_data.get('market_cap', {}).get('usd', 0)
        change_24h = market_data.get('price_change_percentage_24h', 0) or 0
        rank = data.get('market_cap_rank', 'N/A')
        symbol = data.get('symbol', '').upper()

        embed = discord.Embed(
            title=f"{data.get('name')} ({symbol})",
            color=discord.Color.green() if change_24h >= 0 else discord.Color.red()
        )
        embed.set_thumbnail(url=data.get('image', {}).get('large', ''))
        embed.add_field(name="🏆 Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="💰 Price", value=f"${price:,.4f}", inline=True)
        embed.add_field(name="📈 24h Change", value=f"{change_24h:.2f}%", inline=True)
        embed.add_field(name="🏦 Market Cap", value=f"${market_cap:,.0f}", inline=False)
        embed.set_footer(text="Data provided by CoinGecko API")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="info", description="Fetch deskripsi project, fundamental, dan link website resmi.")
    @app_commands.describe(coin="Coin ID di CoinGecko (contoh: bitcoin, ethereum, solana)")
    async def info(self, interaction: discord.Interaction, coin: str):
        await interaction.response.defer()

        coin_id = coin.lower().replace(" ", "-")

        cached = _cache_get(f"info:{coin_id}")
        if cached:
            data = cached
        else:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=true&developer_data=true&sparkline=false"

            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response,
                ):
                    if response.status == 429:
                        await interaction.followup.send(
                            "⏳ CoinGecko rate limit tercapai. Coba lagi dalam 1 menit."
                        )
                        return
                    if response.status != 200:
                        await interaction.followup.send(
                            f"❌ Koin `{coin}` tidak ditemukan (HTTP {response.status})."
                        )
                        return
                    data = await response.json()
                    _cache_set(f"info:{coin_id}", data)
            except aiohttp.ClientError as e:
                await interaction.followup.send(f"❌ Network error: `{e}`")
                return

        desc = data.get('description', {}).get('en', 'No description available.')
        # Strip HTML tags kasar (CoinGecko kadang ngasih <p> dll)
        import re
        desc = re.sub(r'<[^>]+>', '', desc)

        if len(desc) > 1000:
            desc = desc[:1000] + "... [Read more on website]"

        links = data.get('links', {})
        homepage = links.get('homepage', [''])[0]
        github_links = links.get('repos_url', {}).get('github', [])
        github = github_links[0] if github_links else ''

        embed = discord.Embed(
            title=f"Info: {data.get('name')}",
            description=desc,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=data.get('image', {}).get('large', ''))

        if homepage:
            embed.add_field(name="🌐 Website", value=homepage, inline=False)
        if github:
            embed.add_field(name="💻 GitHub", value=github, inline=False)

        embed.set_footer(text="Data provided by CoinGecko API")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CryptoCommands(bot))
