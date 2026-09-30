FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot

# The SQLite database lives in /app/data; mount a volume there to keep orders between restarts.
VOLUME ["/app/data"]
CMD ["python", "-m", "bot"]
