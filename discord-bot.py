"""
FLOW Agent OS — Discord Bot
Bridges Discord messages → AgentZero (Hetzner VPS)
Mounts at: /opt/discord-bot.py
"""

import os
import asyncio
import aiohttp
import discord
from discord.ext import commands

# ── Config from environment ───────────────────────────────────────────────────
DISCORD_TOKEN     = os.environ["DISCORD_TOKEN"]
AGENT_ZERO_URL    = os.environ.get("AGENT_ZERO_URL", "http://5.78.190.199:50001")
AGENT_ZERO_API_KEY = os.environ.get("AGENT_ZERO_API_KEY", "")

# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Helpers ───────────────────────────────────────────────────────────────────
async def send_to_agent_zero(message: str, context_id: str = "discord") -> str:
    """Forward a message to AgentZero and return the response."""
    headers = {
        "Content-Type": "application/json",
    }
    if AGENT_ZERO_API_KEY:
        headers["X-API-Key"] = AGENT_ZERO_API_KEY

    payload = {
        "message": message,
        "context": context_id,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{AGENT_ZERO_URL}/api/message",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # AgentZero returns response in different fields depending on version
                    return (
                        data.get("response")
                        or data.get("message")
                        or data.get("content")
                        or str(data)
                    )
                else:
                    text = await resp.text()
                    return f"AgentZero error {resp.status}: {text[:200]}"
    except aiohttp.ClientConnectorError:
        return f"Cannot reach AgentZero at {AGENT_ZERO_URL} — is it running?"
    except asyncio.TimeoutError:
        return "AgentZero timed out (>120s). Task may still be running."
    except Exception as e:
        return f"Error: {e}"


# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[FLOW Bot] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[FLOW Bot] AgentZero endpoint: {AGENT_ZERO_URL}")


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
        await message.reply("Send me a task and I'll route it to AgentZero.")
        return

    # Show typing indicator while waiting
    async with message.channel.typing():
        context_id = str(message.author.id)
        response = await send_to_agent_zero(content, context_id)

    # Discord has a 2000 char message limit — split if needed
    if len(response) <= 2000:
        await message.reply(response)
    else:
        chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)

    await bot.process_commands(message)


# ── Commands ──────────────────────────────────────────────────────────────────
@bot.command(name="ping")
async def ping(ctx):
    """Check if the bot and AgentZero are reachable."""
    await ctx.send("Bot is up. Checking AgentZero...")
    result = await send_to_agent_zero("ping", "health-check")
    await ctx.send(f"AgentZero response: {result[:500]}")


@bot.command(name="task")
async def task(ctx, *, message: str):
    """Send a task directly to AgentZero. Usage: !task <your task>"""
    async with ctx.typing():
        response = await send_to_agent_zero(message, str(ctx.author.id))
    if len(response) <= 2000:
        await ctx.reply(response)
    else:
        chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
        for i, chunk in enumerate(chunks):
            await ctx.send(chunk)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
