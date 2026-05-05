import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class CryptoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="search", description="Fetch harga real-time, Market Cap, 24h change, dan Rank.")
    @app_commands.describe(coin="Coin ID di CoinGecko (contoh: bitcoin, ethereum, solana)")
    async def search(self, interaction: discord.Interaction, coin: str):
        # Gunakan defer karena API request bisa memakan waktu lebih dari 3 detik
        await interaction.response.defer()
        
        coin_id = coin.lower().replace(" ", "-")
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"❌ Koin `{coin}` tidak ditemukan atau API rate limit tercapai.")
                    return
                data = await response.json()
                
        market_data = data.get('market_data', {})
        price = market_data.get('current_price', {}).get('usd', 0)
        market_cap = market_data.get('market_cap', {}).get('usd', 0)
        change_24h = market_data.get('price_change_percentage_24h', 0)
        rank = data.get('market_cap_rank', 'N/A')
        symbol = data.get('symbol', '').upper()
        
        # Format Embed
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
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=true&developer_data=true&sparkline=false"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await interaction.followup.send(f"❌ Koin `{coin}` tidak ditemukan atau API rate limit tercapai.")
                    return
                data = await response.json()
        
        # Ambil deskripsi dalam bahasa Inggris
        desc = data.get('description', {}).get('en', 'No description available.')
        
        # Limit panjang deskripsi agar Embed tidak error (Maksimal 4096 karakter, tapi kita batasi 1000 agar rapi)
        if len(desc) > 1000:
            desc = desc[:1000] + "... [Read more on website]"
            
        links = data.get('links', {})
        homepage = links.get('homepage', [''])[0]
        github_links = links.get('repos_url', {}).get('github', [])
        github = github_links[0] if github_links else ''
        
        # Format Embed
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
