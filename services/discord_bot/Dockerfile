FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir discord.py aiohttp

COPY discord-bot.py .

CMD ["python", "discord-bot.py"]
