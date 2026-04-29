"""
FLOW Agent AS — Discord Bot
Bridges Discord messages → BizBrain Lite intake pipeline
"""

import os
import asyncio
import uuid
import aiohttp
import discord
from datetime import datetime, timezone
from discord.ext import commands

# ── Config from environment ───────────────────────────────────────────────────
DISCORD_TOKEN      = os.environ["DISCORD_TOKEN"]
BIZBRAIN_URL       = os.environ.get("BIZBRAIN_URL", "http://bizbrain-lite:8000")
BIZBRAIN_API_TOKEN = os.environ.get("BIZBRAIN_API_TOKEN", "")

# ── Task type detection ───────────────────────────────────────────────────────

def detect_task(content: str) -> tuple[str, str]:
    """Return (task_type, preferred_owner) based on message keywords."""
    c = content.lower()
    if any(w in c for w in ["build", "create landing", "implement", "develop", "code", "html", "landing page", "website"]):
        return "implementation", "agent_zero"
    if any(w in c for w in ["classify", "categorize", "sort", "route", "analyse", "analyze"]):
        return "classification", "openclaw"
    # Default: content writing → Hermes
    return "content_prep", "hermes"


# ── BizBrain intake ───────────────────────────────────────────────────────────

async def submit_to_bizbrain(message: str, context_id: str) -> dict:
    """Submit a task envelope to BizBrain intake. Returns the response dict."""
    task_type, owner = detect_task(message)
    task_id = str(uuid.uuid4())

    envelope = {
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "discord",
        "title": message[:120].strip(),
        "goal": message.strip(),
        "task_type": task_type,
        "risk_tier": "low",
        "preferred_owner": owner,
        "inputs": {"discord_user_id": context_id},
        "output_required": "Completed deliverable written to runtime/reviews/",
        "review_required": False,
        "rollback_required": False,
        "status": "pending",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Token": BIZBRAIN_API_TOKEN,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BIZBRAIN_URL}/v1/intake/task",
                json=envelope,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                return {"ok": resp.status == 200, "data": data, "task_type": task_type, "owner": owner}
    except aiohttp.ClientConnectorError:
        return {"ok": False, "error": f"Cannot reach BizBrain at {BIZBRAIN_URL}"}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "BizBrain timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[FLOW Bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[FLOW Bot] BizBrain endpoint: {BIZBRAIN_URL}")


@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Only respond to DMs or when mentioned
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions

    if not (is_dm or is_mentioned):
        await bot.process_commands(message)
        return

    # Strip the mention prefix if present
    content = message.content
    if is_mentioned:
        content = content.replace(f"<@{bot.user.id}>", "").strip()
        content = content.replace(f"<@!{bot.user.id}>", "").strip()

    if not content:
        await message.reply("Send me a task and I'll route it through FLOW.")
        return

    # Submit to BizBrain and reply immediately with job ID
    async with message.channel.typing():
        context_id = str(message.author.id)
        result = await submit_to_bizbrain(content, context_id)

    if not result.get("ok"):
        await message.reply(f"FLOW intake error: {result.get('error', 'unknown')}")
        return

    data = result["data"]
    job_id = data.get("job_id", "unknown")
    owner = data.get("owner", result.get("owner", "?"))
    task_type = result.get("task_type", "?")

    await message.reply(
        f"**Job accepted** — routed to **{owner.upper()}**\n"
        f"Type: `{task_type}` · ID: `{job_id}`\n"
        f"Results will post to the output channel when ready."
    )

    await bot.process_commands(message)


# ── Commands ──────────────────────────────────────────────────────────────────
@bot.command(name="ping")
async def ping(ctx):
    """Check if the bot and BizBrain are reachable."""
    await ctx.send("Bot is up. Checking BizBrain...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BIZBRAIN_URL}/v1/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                await ctx.send(f"BizBrain status: HTTP {resp.status}")
    except Exception as e:
        await ctx.send(f"BizBrain unreachable: {e}")


@bot.command(name="task")
async def task(ctx, *, message: str):
    """Submit a task directly to FLOW. Usage: !task <your task>"""
    async with ctx.typing():
        result = await submit_to_bizbrain(message, str(ctx.author.id))

    if not result.get("ok"):
        await ctx.reply(f"FLOW error: {result.get('error', 'unknown')}")
        return

    data = result["data"]
    await ctx.reply(
        f"**Job accepted** — `{data.get('owner', '?').upper()}`\n"
        f"ID: `{data.get('job_id', '?')}`\n"
        f"Results will post when ready."
    )


@bot.command(name="status")
async def status(ctx):
    """Check FLOW queue depths."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BIZBRAIN_URL}/v1/intake/queues/status",
                headers={"X-Api-Token": BIZBRAIN_API_TOKEN},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                queues = data.get("queues", {})
                lines = [f"**FLOW Queue Status**"]
                for owner, depth in queues.items():
                    lines.append(f"• {owner}: {depth} jobs")
                lines.append(f"Total: {data.get('total', 0)}")
                await ctx.send("\n".join(lines))
    except Exception as e:
        await ctx.send(f"Could not fetch queue status: {e}")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
