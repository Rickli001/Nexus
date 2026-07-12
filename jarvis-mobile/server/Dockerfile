# Build from the jarvis-mobile/ directory:
#   docker build -f server/Dockerfile -t jarvis .
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server server
COPY app app

WORKDIR /srv/server
EXPOSE 8741
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8741"]
