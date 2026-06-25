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
load_dotenv()  # Current directory
load_dotenv(pathlib.Path("/etc/secrets/.env"))  # Render secret files path

# Flask Setup
app = Flask(__name__)
bot_name = "ff-uid-info"

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

# If still no token, try current directory .env
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
            command_prefix="!",  # Prefix commands (optional)
            intents=intents,
            help_command=None
        )
        self.session = None
        self.default_region = DEFAULT_REGION

    async def setup_hook(self):
        """Setup ho raha hai — cogs load aur commands sync"""
        self.session = aiohttp.ClientSession()
        
        # INFO: Cogs folder mein infoCommands.py hona chahiye
        try:
            await self.load_extension("cogs.infoCommands")
            print("✅ Loaded InfoCommands cog")
        except Exception as e:
            print(f"❌ Failed to load cog: {e}")
            traceback.print_exc()
            print("\n💡 TIP: Make sure 'cogs/infoCommands.py' exists!")
        
        # Sync slash commands globally
        await self.tree.sync()
        print("✅ Slash commands synced globally")
        
        # Start status update loop
        self.update_status.start()

    async def on_ready(self):
        global bot_name
        bot_name = str(self.user)
        
        print(f"\n{'='*50}")
        print(f"✅ Connected as {bot_name}")
        print(f"🌐 In {len(self.guilds)} servers")
        print(f"📝 Invite Link: https://discord.com/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot%20applications.commands")
        print(f"{'='*50}\n")
        
        # Flask server for hosting platforms (Render, etc.)
        if os.environ.get('RENDER'):
            import threading
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            print("🚀 Flask server started on port 10000")
        
        # Set initial status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /info UID"
        )
        await self.change_presence(activity=activity)

    @tasks.loop(minutes=5)
    async def update_status(self):
        """Bot status update every 5 minutes"""
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
        """Clean shutdown"""
        if self.session:
            await self.session.close()
        await super().close()


# ==================== CREATE BOT INSTANCE ====================
bot = Bot()


# ==================== DEBUG COMMANDS ====================
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! `{latency}ms`")


@bot.tree.command(name="sync", description="Sync slash commands (Owner only)")
async def sync_commands(interaction: discord.Interaction):
    # Owner check — apne user ID se replace karo
    owner_id = 869918246441218088  # 🔥 APNI DISCORD USER ID YAHAN DAALO 🔥
    
    if interaction.user.id == owner_id:
        await bot.tree.sync()
        await interaction.response.send_message("✅ Commands synced globally!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)


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
    # Render.com ya other hosting platforms ke liye
    if os.environ.get('RENDER'):
        asyncio.run(main())
    else:
        # Local run
        bot.run(TOKEN)
