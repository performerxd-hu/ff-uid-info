import discord
from discord.ext import commands, tasks
import os
import traceback
from flask import Flask
import sys
import aiohttp
import asyncio
from dotenv import load_dotenv
import pathlib

# Try to load .env from multiple possible locations
load_dotenv()
load_dotenv(pathlib.Path("/etc/secrets/.env"))

# Flask Setup
app = Flask(__name__)
bot_name = "FF-UID-TO-INFO"

@app.route('/')
def home():
    return f"✅ {bot_name} is operational"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Discord Bot
TOKEN = os.getenv("TOKEN")

# If TOKEN is still missing, try to read from .env file directly
if not TOKEN:
    try:
        env_path = pathlib.Path("/etc/secrets/.env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('TOKEN='):
                        TOKEN = line.strip().split('=')[1]
                        break
    except:
        pass

if not TOKEN:
    try:
        env_path = pathlib.Path(".env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('TOKEN='):
                        TOKEN = line.strip().split('=')[1]
                        break
    except:
        pass

if not TOKEN:
    raise ValueError("Missing TOKEN in environment. Please add TOKEN as an environment variable or secret file.")

# Default region for Free Fire
DEFAULT_REGION = "IND"

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.session = None
        self.default_region = DEFAULT_REGION

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        
        try:
            await self.load_extension("cogs.infoCommands")
            print("✅ Loaded InfoCommands cog")
        except Exception as e:
            print(f"❌ Failed to load cog: {e}")
            traceback.print_exc()
        
        await self.tree.sync()
        print("✅ Slash commands synced globally")
        self.update_status.start()

    async def on_ready(self):
        global bot_name
        bot_name = str(self.user)
        
        print(f"\n{'='*50}")
        print(f"✅ Connected as {bot_name}")
        print(f"🌐 In {len(self.guilds)} servers")
        print(f"{'='*50}\n")
        
        if os.environ.get('RENDER'):
            import threading
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            print("🚀 Flask server started on port 10000")
        
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /info UID"
        )
        await self.change_presence(activity=activity)

    @tasks.loop(minutes=5)
    async def update_status(self):
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /info UID"
            )
            await self.change_presence(activity=activity)
        except Exception as e:
            print(f"Status update error: {e}")

    @update_status.before_loop
    async def before_status_update(self):
        await self.wait_until_ready()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = Bot()

# ==================== OWNER ID ====================
OWNER_ID = 869918246441218088  # 🔥 APNI DISCORD USER ID YAHAN DAALO 🔥

# ==================== SLASH COMMANDS ====================
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! `{latency}ms`")

@bot.tree.command(name="sync", description="Sync slash commands (Owner only)")
async def sync_commands(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    await bot.tree.sync()
    await interaction.followup.send("✅ Commands synced globally!", ephemeral=True)

# ==================== PREFIX COMMAND (Fallback) ====================
@bot.command(name="info")
async def info_prefix(ctx, uid: str):
    """Get FreeFire player info (prefix command)"""
    if not uid.isdigit() or len(uid) < 6:
        await ctx.send("❌ Invalid UID. Must be at least 6 digits.")
        return
    
    await ctx.send("⏳ Fetching player data...")
    
    try:
        async with aiohttp.ClientSession() as session:
            api_url = f"http://raw.thug4ff.xyz/info?uid={uid}&key=great&region={DEFAULT_REGION}"
            async with session.get(api_url) as response:
                if response.status != 200:
                    await ctx.send("❌ API error. Try again later.")
                    return
                data = await response.json()
        
        basic_info = data.get('basicInfo', {})
        clan_info = data.get('clanBasicInfo', {})
        credit_score_info = data.get('creditScoreInfo', {})
        pet_info = data.get('petInfo', {})
        profile_info = data.get('profileInfo', {})
        social_info = data.get('socialInfo', {})
        
        nickname = basic_info.get('nickname', 'Unknown')
        region = basic_info.get('region', DEFAULT_REGION).upper()
        
        embed = discord.Embed(
            title=f"🎮 {nickname}",
            description=f"**UID:** `{uid}` | **Region:** `{region}`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📊 Account Basic Info",
            value=f"```\n"
                  f"Level: {basic_info.get('level', 'N/A')}\n"
                  f"Likes: {basic_info.get('liked', 'N/A')}\n"
                  f"Honor Score: {credit_score_info.get('creditScore', 'N/A')}\n"
                  f"Signature: {social_info.get('signature', 'None')[:50]}\n"
                  f"```",
            inline=False
        )
        embed.add_field(
            name="🏆 Ranks",
            value=f"```\n"
                  f"BR Rank: {basic_info.get('rank', 'N/A')}\n"
                  f"CS Rank: {basic_info.get('csRank', 'N/A')}\n"
                  f"```",
            inline=True
        )
        
        if clan_info:
            embed.add_field(
                name="👥 Clan Info",
                value=f"```\n"
                      f"Name: {clan_info.get('clanName', 'N/A')}\n"
                      f"Level: {clan_info.get('clanLevel', 'N/A')}\n"
                      f"Members: {clan_info.get('memberNum', '0')}/{clan_info.get('capacity', '0')}\n"
                      f"```",
                inline=False
            )
        
        if pet_info and pet_info.get('isSelected'):
            embed.add_field(
                name="🐾 Pet Info",
                value=f"```\n"
                      f"Name: {pet_info.get('name', 'N/A')}\n"
                      f"Level: {pet_info.get('level', 'N/A')}\n"
                      f"```",
                inline=True
            )
        
        embed.set_footer(text="FF-UID-TO-INFO | Data from FreeFire API")
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:100]}")

# ==================== MAIN ====================
async def main():
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n[!] Bot stopped by user")
        await bot.close()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        await bot.close()

if __name__ == "__main__":
    if os.environ.get('RENDER'):
        asyncio.run(main())
    else:
        bot.run(TOKEN)
