FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
USER root
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg pulseaudio pulseaudio-utils xvfb xauth && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=pwuser:pwuser . .
RUN mkdir -p /app/data /home/pwuser/.cache && chown -R pwuser:pwuser /app /home/pwuser/.cache
USER pwuser
ENV PYTHONUNBUFFERED=1 BIND_HOST=0.0.0.0 DATA_DIR=/app/data PULSE_SINK=meet
EXPOSE 8000
CMD ["bash", "start.sh"]
