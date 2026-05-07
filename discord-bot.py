"""
FLOW Agent AS Discord control bot.

Discord is a control surface only: it submits validated task envelopes, reads
queue state, blocks tasks, and records explicit Gamma approvals through the
FLOW API. It never executes production work directly.
"""

from __future__ import annotations

import os
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
BIZBRAIN_URL = os.environ.get("BIZBRAIN_URL", "http://flow-orchestrator:8000")
BIZBRAIN_API_TOKEN = os.environ.get("BIZBRAIN_API_TOKEN", "")


def headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "X-Api-Token": BIZBRAIN_API_TOKEN}


async def flow_get(path: str) -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BIZBRAIN_URL}/v1/flow{path}",
            headers=headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            data = await response.json()
            if response.status >= 400:
                raise RuntimeError(data.get("detail", f"HTTP {response.status}"))
            return data


async def flow_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BIZBRAIN_URL}/v1/flow{path}",
            json=payload,
            headers=headers(),
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            data = await response.json()
            if response.status >= 400:
                raise RuntimeError(data.get("detail", f"HTTP {response.status}"))
            return data


def task_lines(tasks: list[dict[str, Any]], empty: str) -> str:
    if not tasks:
        return empty
    lines = []
    for task in tasks[:15]:
        lines.append(
            f"`{task['task_id']}` | {task.get('owner_role', '?')} | {task.get('status', '?')} | {task.get('title', '')[:80]}"
        )
    return "\n".join(lines)


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


flow_group = app_commands.Group(name="flow", description="Control FLOW Agent AS tasks")


@flow_group.command(name="status", description="Show agent runtime health and queue counts")
async def flow_status(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    data = await flow_get("/status")
    agents = data["agents"]
    queues = data["queues"]
    lines = ["FLOW status"]
    for key in ("alpha", "beta", "gamma"):
        agent = agents[key]
        marker = "OK" if agent["healthy"] else "CHECK"
        lines.append(
            f"{marker} {agent['name']}: port {agent['port']} open={agent['port_open']} runtime={agent['runtime_registered']}"
        )
    lines.append(
        "Queues: "
        + ", ".join(f"{name}={queues.get(name, 0)}" for name in ("pending", "active", "completed", "escalated", "blocked"))
    )
    await interaction.followup.send("\n".join(lines), ephemeral=True)


@flow_group.command(name="submit", description="Submit a validated FLOW task envelope")
@app_commands.describe(
    title="Short task title",
    goal="Observable task goal",
    risk_tier="reputation, time_loss, or downtime_security_money",
)
async def flow_submit(
    interaction: discord.Interaction,
    title: str,
    goal: str,
    risk_tier: str,
) -> None:
    await interaction.response.defer(ephemeral=True)
    payload = {
        "title": title,
        "goal": goal,
        "risk_tier": risk_tier,
        "source": "discord",
        "inputs": {"discord_user_id": str(interaction.user.id)},
    }
    data = await flow_post("/submit", payload)
    task = data["task"]
    await interaction.followup.send(
        f"Accepted `{task['task_id']}` -> {task['owner_role']} / {task['queue']} / {task['status']}",
        ephemeral=True,
    )


async def send_queue(interaction: discord.Interaction, queue: str) -> None:
    await interaction.response.defer(ephemeral=True)
    data = await flow_get(f"/tasks?queue={queue}")
    await interaction.followup.send(task_lines(data["tasks"], f"No {queue} tasks."), ephemeral=True)


@flow_group.command(name="pending", description="List pending tasks")
async def flow_pending(interaction: discord.Interaction) -> None:
    await send_queue(interaction, "pending")


@flow_group.command(name="active", description="List active tasks")
async def flow_active(interaction: discord.Interaction) -> None:
    await send_queue(interaction, "active")


@flow_group.command(name="completed", description="List completed tasks")
async def flow_completed(interaction: discord.Interaction) -> None:
    await send_queue(interaction, "completed")


@flow_group.command(name="escalated", description="List escalated/Gamma review tasks")
async def flow_escalated(interaction: discord.Interaction) -> None:
    await send_queue(interaction, "escalated")


@flow_group.command(name="artifact", description="Fetch artifact path and output summary")
async def flow_artifact(interaction: discord.Interaction, task_id: str) -> None:
    await interaction.response.defer(ephemeral=True)
    task = await flow_get(f"/tasks/{task_id}")
    artifact_path = task.get("artifact_path")
    review_paths = task.get("review_artifacts", {})
    audit_count = len(task.get("audit", []))
    lines = [f"Task `{task_id}`", f"Status: {task.get('status')} | queue: {task.get('queue')}"]
    if artifact_path:
        lines.append(f"Output: `{artifact_path}`")
    if review_paths:
        lines.append("Review artifacts: " + ", ".join(f"{key}=`{value}`" for key, value in review_paths.items()))
    lines.append(f"Audit events: {audit_count}")
    await interaction.followup.send("\n".join(lines), ephemeral=True)


@flow_group.command(name="approve", description="Explicitly approve a Gamma review task")
async def flow_approve(interaction: discord.Interaction, task_id: str) -> None:
    await interaction.response.defer(ephemeral=True)
    data = await flow_post("/approve", {"task_id": task_id, "actor": f"discord:{interaction.user.id}"})
    task = data["task"]
    await interaction.followup.send(
        f"Gamma approval recorded for `{task_id}`. Task moved to `{task['queue']}` as `{task['status']}`.",
        ephemeral=True,
    )


@flow_group.command(name="block", description="Block or cancel a task with a reason")
async def flow_block(interaction: discord.Interaction, task_id: str, reason: str) -> None:
    await interaction.response.defer(ephemeral=True)
    data = await flow_post(
        "/block",
        {"task_id": task_id, "reason": reason, "actor": f"discord:{interaction.user.id}"},
    )
    task = data["task"]
    await interaction.followup.send(f"Blocked `{task_id}`: {task.get('status')}", ephemeral=True)


@bot.event
async def on_ready() -> None:
    if flow_group not in bot.tree.get_commands():
        bot.tree.add_command(flow_group)
    await bot.tree.sync()
    print(f"[FLOW Bot] Logged in as {bot.user} | API={BIZBRAIN_URL}")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
