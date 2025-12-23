import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta
import pytz
import json
import os
from discord.errors import NotFound

# ───────── CONFIG ─────────
STATUS_CHANNEL_ID = 1452954348844880043
COUNTDOWN_CHANNEL_ID = 1452978877491314739

DATA_FILE = "bot_state.json"

TIMEZONE = pytz.timezone("Asia/Kolkata")

RESTART_TIMES = [
    time(5, 0),
    time(17, 0)
]

CHECK_INTERVAL = 20

# ───────── DISCORD SETUP ─────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

status_msg_id = None
last_restart_handled = None
countdown_placeholder_id = None

# ───────── STORAGE ─────────
def load_state():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ───────── TIME HELPERS ─────────
def now_ist():
    return datetime.now(TIMEZONE)

def get_today_restart_times():
    now = now_ist()
    return [
        now.replace(hour=rt.hour, minute=rt.minute, second=0, microsecond=0)
        for rt in RESTART_TIMES
    ]

def get_next_restart():
    now = now_ist()
    for rt in get_today_restart_times():
        if rt > now:
            return rt
    return get_today_restart_times()[0] + timedelta(days=1)

# ───────── PLACEHOLDER ─────────
async def ensure_placeholder(channel):
    global countdown_placeholder_id

    if countdown_placeholder_id:
        try:
            await channel.fetch_message(countdown_placeholder_id)
            return
        except:
            countdown_placeholder_id = None

    msg = await channel.send(
         "☀️ **THE EXILED LANDS STAND STRONG** ☀️\n\n"
    "The world is stable.\n"
    "Steel is sharp.\n"
    "The gods are watching.\n\n"
    "🟢 **World Status:** ONLINE\n\n"
    "Next scheduled reforging:\n"
    "🕔 5:00 AM & 5:00 PM IST"
    )
    countdown_placeholder_id = msg.id

# ───────── BOT READY ─────────
@bot.event
async def on_ready():
    global status_msg_id, last_restart_handled
    print(f"{bot.user} now watches the Exiled Lands")

    state = load_state()
    status_msg_id = state.get("status_msg")
    last_restart_handled = state.get("last_restart")

    status_loop.start()
    countdown_loop.start()

# ───────── SERVER STATUS LOOP (SELF-HEALING) ─────────
@tasks.loop(seconds=CHECK_INTERVAL)
async def status_loop():
    global status_msg_id

    channel = bot.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        return

    # Create message if missing
    if status_msg_id is None:
        msg = await channel.send("🌑 The Exiled Lands await their fate…")
        status_msg_id = msg.id
        save_state({"status_msg": status_msg_id, "last_restart": last_restart_handled})
        return

    try:
        msg = await channel.fetch_message(status_msg_id)
    except NotFound:
        # Message was deleted — recreate
        msg = await channel.send("🌑 The Exiled Lands await their fate…")
        status_msg_id = msg.id
        save_state({"status_msg": status_msg_id, "last_restart": last_restart_handled})

    now = now_ist()
    restart = get_next_restart()

    if restart <= now <= restart + timedelta(minutes=2):
        content = (
            "🌑 **THE EXILED LANDS ARE BEING REFORGED** 🌑\n\n"
            "The gods reshape the world.\n"
            "Steel rests. Time stands still.\n\n"
            "🔴 **World Status:** OFFLINE\n\n"
            "Return shortly, exile."
        )
    else:
        content = (
            "☀️ **THE EXILED LANDS STAND STRONG** ☀️\n\n"
            "Steel is sharp.\n"
            "The gods are watching.\n\n"
            "🟢 **World Status:** ONLINE\n\n"
            "Sharpen your blade.\n"
            "Survival favors the prepared."
        )

    await msg.edit(content=content)

# ───────── COUNTDOWN LOOP (UNCHANGED) ─────────
@tasks.loop(seconds=CHECK_INTERVAL)
async def countdown_loop():
    global last_restart_handled, countdown_placeholder_id

    channel = bot.get_channel(COUNTDOWN_CHANNEL_ID)
    if not channel:
        return

    await ensure_placeholder(channel)

    now = now_ist()
    restart = get_next_restart()
    diff = int((restart - now).total_seconds())

    restart_key = restart.strftime("%Y-%m-%d %H:%M")
    if last_restart_handled == restart_key:
        return

    async def remove_placeholder():
        global countdown_placeholder_id
        if countdown_placeholder_id:
            try:
                msg = await channel.fetch_message(countdown_placeholder_id)
                await msg.delete()
            except:
                pass
            countdown_placeholder_id = None

    if diff == 600:
        await remove_placeholder()
        await channel.send("⚔️ **THE GODS CALL FOR REST** ⚔️\n\nRestart in **10 minutes**.")

    elif diff == 300:
        await channel.send("⚔️ **THE GODS GROW IMPATIENT** ⚔️\n\nRestart in **5 minutes**.")

    elif diff == 180:
        await channel.send("🔥 **THE WORLD SHUDDERS** 🔥\n\nRestart in **3 minutes**.")

    elif diff == 120:
        await channel.send("🔥 **THE WORLD TREMBLES** 🔥\n\nRestart in **2 minutes**.")

    elif diff == 60:
        await channel.send("🌑 **THE END DRAWS NEAR** 🌑\n\nRestart in **1 minute**.")

    elif diff <= 0:
        msg = await channel.send(
            "🌑 **THE WORLD FALLS SILENT** 🌑\n\nRestarting now.\nDo not attempt to join."
        )

        await discord.utils.sleep_until(restart + timedelta(minutes=2))

        await msg.edit(
            content="☀️ **THE WORLD IS REBORN** ☀️\n\nYou may return, exile."
        )

        last_restart_handled = restart_key
        save_state({"status_msg": status_msg_id, "last_restart": last_restart_handled})
        await ensure_placeholder(channel)

# ───────── RUN ─────────
import os
bot.run(os.getenv("MTM3NDExOTU4MzgzNzA2MTIxMA.Gwbqzt.0mGRkhhb_vS6nor5Wi8kBN2FONxEIQMZXDKC6U"))
