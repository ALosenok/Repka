FROM python:3.10.16-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip install --no-cahe-dir -r requirements.txt

COPY Telegram_Bot.py /app

ENV BOT_TOKEN = bot_token

CMD ["python", "Telegram_Bot.py"]
