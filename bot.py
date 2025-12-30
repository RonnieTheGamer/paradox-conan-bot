import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta
import pytz
import os

# ================= CONFIG =================
SERVER_STATUS_CHANNEL = 1452954348844880043  # 🔴 replace
RESTART_CHANNEL = 1452978877491314739       # 🔴 replace

TIMEZONE = pytz.timezone("Asia/Kolkata")
RESTART_TIMES = [time(5, 10), time(17, 10)]

CHECK_INTERVAL = 5  # seconds
# =========================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

status_message_id = None
restart_message_id = None
countdown_stage = None

# ---------- TIME HELPERS ----------
def now():
    return datetime.now(TIMEZONE)

def next_restart():
    n = now()
    today = n.date()
    times = [datetime.combine(today, t, tzinfo=TIMEZONE) for t in RESTART_TIMES]
    for t in times:
        if t > n:
            return t
    return times[0] + timedelta(days=1)

# ---------- SERVER STATUS ----------
@tasks.loop(seconds=CHECK_INTERVAL)
async def server_status_loop():
    global status_message_id

    channel = bot.get_channel(SERVER_STATUS_CHANNEL)
    if not channel:
        return

    if not status_message_id:
        msg = await channel.send("Initializing world status…")
        status_message_id = msg.id

    msg = await channel.fetch_message(status_message_id)
    n = now()
    r = next_restart()

    if r <= n <= r + timedelta(minutes=2):
        content = (
            "🌑 **THE WORLD FALLS SILENT** 🌑\n\n"
            "The gods reshape the land.\n"
            "Time stands still.\n\n"
            "🔴 **World Status:** OFFLINE"
        )
    else:
        content = (
            "☀️ **THE EXILED LANDS STAND STRONG** ☀️\n\n"
            "Steel is sharp.\n"
            "The gods are watching.\n\n"
            "🟢 **World Status:** ONLINE"
        )

    if msg.content != content:
        await msg.edit(content=content)

# ---------- RESTART / COUNTDOWN ----------
@tasks.loop(seconds=CHECK_INTERVAL)
async def restart_loop():
    global countdown_stage, restart_message_id

    channel = bot.get_channel(RESTART_CHANNEL)
    if not channel:
        return

    n = now()
    r = next_restart()
    diff = int((r - n).total_seconds())

    # -------- COUNTDOWN (NO EDITS) --------
    if 600 >= diff > 590 and countdown_stage != "10":
        await channel.send("⚔️ **THE GODS CALL FOR REST** ⚔️\nThe world will be reforged in **10 minutes**.")
        countdown_stage = "10"

    elif 300 >= diff > 290 and countdown_stage != "5":
        await channel.send("⚔️ **THE GODS GROW IMPATIENT** ⚔️\nThe world will be reforged in **5 minutes**.")
        countdown_stage = "5"

    elif 180 >= diff > 170 and countdown_stage != "3":
        await channel.send("🔥 **THE WORLD SHUDDERS** 🔥\nServer restarting in **3 minutes**.")
        countdown_stage = "3"

    elif 120 >= diff > 110 and countdown_stage != "2":
        await channel.send("🔥 **THE WORLD TREMBLES** 🔥\nServer restarting in **2 minutes**.")
        countdown_stage = "2"

    elif 60 >= diff > 50 and countdown_stage != "1":
        await channel.send("🌑 **THE END DRAWS NEAR** 🌑\nServer restarting in **1 minute**.")
        countdown_stage = "1"

    elif 5 >= diff > 0 and countdown_stage != "now":
        msg = await channel.send("💀 **THE FINAL MOMENT** 💀\nRestarting now…")
        restart_message_id = msg.id
        countdown_stage = "now"

    # -------- RESTART WINDOW (EDIT ONLY) --------
    if diff <= 0 and restart_message_id:
        msg = await channel.fetch_message(restart_message_id)

        if diff >= -60:
            await msg.edit(content="🌑 **THE WORLD FALLS SILENT** 🌑\nRestart in progress.\nThe gods reclaim the land.")
        elif diff >= -120:
            await msg.edit(content="⏳ **THE GODS ARE AT WORK** ⏳\nHold your patience, exile.")
        else:
            await msg.edit(
                content="☀️ **THE WORLD IS REBORN** ☀️\nThe Exiled Lands breathe again."
            )
            await channel.purge(limit=20)
            await channel.send(
                "☀️ **THE EXILED LANDS STAND STRONG** ☀️\n\n"
                "🟢 Server Status: ONLINE\n\n"
                "Next reforging:\n🕔 **5:10 AM & 5:10 PM IST**"
            )
            countdown_stage = None
            restart_message_id = None

# ---------- READY ----------
@bot.event
async def on_ready():
    print(f"{bot.user} has awakened.")
    server_status_loop.start()
    restart_loop.start()

bot.run(os.getenv("BOT_TOKEN"))
