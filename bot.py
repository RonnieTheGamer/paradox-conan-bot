import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta
import pytz
import json
import os
from discord.errors import NotFound

# ───────── CONFIG ─────────
STATUS_CHANNEL_ID = 1452954348844880043      # server-status channel ID
COUNTDOWN_CHANNEL_ID = 1452978877491314739   # server-restarts channel ID

DATA_FILE = "bot_state.json"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# 🔁 RESTART TIMES (5:10 AM / 5:10 PM)
RESTART_TIMES = [
    time(5, 10),
    time(17, 10)
]

CHECK_INTERVAL = 20  # seconds

# ───────── DISCORD SETUP ─────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

status_msg_id = None
last_restart_handled = None
countdown_placeholder_id = None
countdown_stage = None

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
        "🕔 **5:10 AM & 5:10 PM IST**"
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

# ───────── SERVER STATUS LOOP ─────────
@tasks.loop(seconds=CHECK_INTERVAL)
async def status_loop():
    global status_msg_id

    channel = bot.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        return

    if status_msg_id is None:
        msg = await channel.send("🌑 The Exiled Lands await their fate…")
        status_msg_id = msg.id
        save_state({"status_msg": status_msg_id, "last_restart": last_restart_handled})
        return

    try:
        msg = await channel.fetch_message(status_msg_id)
    except NotFound:
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

# ───────── COUNTDOWN LOOP (WINDOW-BASED) ─────────
@tasks.loop(seconds=CHECK_INTERVAL)
async def countdown_loop():
    global last_restart_handled, countdown_placeholder_id, countdown_stage

    channel = bot.get_channel(COUNTDOWN_CHANNEL_ID)
    if not channel:
        return

    await ensure_placeholder(channel)

    now = now_ist()
    restart = get_next_restart()
    diff = int((restart - now).total_seconds())

    restart_key = restart.strftime("%Y-%m-%d %H:%M")

    # Reset stage after restart fully done
    if diff < -120:
        countdown_stage = None
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

    # 🟡 10 MIN (5:00)
    if 600 >= diff > 540 and countdown_stage != "10m":
        await remove_placeholder()
        await channel.send(
            "⚔️ **THE GODS CALL FOR REST** ⚔️\n\n"
            "The world will be reforged in **10 minutes**.\n\n"
            "Prepare, exile."
        )
        countdown_stage = "10m"

    # 🟡 5 MIN (5:05)
    elif 300 >= diff > 240 and countdown_stage != "5m":
        await channel.send(
            "⚔️ **THE GODS GROW IMPATIENT** ⚔️\n\n"
            "The world will be reforged in **5 minutes**."
        )
        countdown_stage = "5m"

    # 🟠 3 MIN (5:07)
    elif 180 >= diff > 120 and countdown_stage != "3m":
        await channel.send(
            "🔥 **THE WORLD SHUDDERS** 🔥\n\n"
            "Server restarting in **3 minutes**."
        )
        countdown_stage = "3m"

    # 🔴 2 MIN (5:08)
    elif 120 >= diff > 60 and countdown_stage != "2m":
        await channel.send(
            "🔥 **THE WORLD TREMBLES** 🔥\n\n"
            "Server restarting in **2 minutes**."
        )
        countdown_stage = "2m"

    # 🔴 1 MIN (5:09)
    elif 60 >= diff > 0 and countdown_stage != "1m":
        await channel.send(
            "🌑 **THE END DRAWS NEAR** 🌑\n\n"
            "Server restarting in **1 minute**."
        )
        countdown_stage = "1m"

    # ⬛ RESTARTING (5:10)
    elif diff <= 0 and countdown_stage != "restart":
        msg = await channel.send(
            "🌑 **THE WORLD FALLS SILENT** 🌑\n\n"
            "Restarting now.\n"
            "Do not attempt to join."
        )
        countdown_stage = "restart"

        await discord.utils.sleep_until(restart + timedelta(minutes=2))

        await msg.edit(
            content=(
                "☀️ **THE WORLD IS REBORN** ☀️\n\n"
                "The Exiled Lands breathe once more.\n"
                "You may return, exile."
            )
        )

        last_restart_handled = restart_key
        save_state({"status_msg": status_msg_id, "last_restart": last_restart_handled})
        await ensure_placeholder(channel)

# ───────── RUN ─────────
import os
bot.run(os.getenv("BOT_TOKEN"))
