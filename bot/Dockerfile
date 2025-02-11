FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy bot code
COPY ai_bot.py .

CMD ["python", "-u", "ai_bot.py"] 