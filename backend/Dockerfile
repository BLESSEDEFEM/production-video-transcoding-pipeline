# ─────────────────────────────────────────────────────────────────
# STAGE 1: BASE IMAGE
# ─────────────────────────────────────────────────────────────────
# Think of this as: "start with a computer that already has Python 3.11"
# python:3.11-slim = Python 3.11 on a minimal Linux (Debian)
# "slim" means no extra unnecessary tools → smaller final image
# FROM python:3.11-slim
FROM python:3.11-slim-bookworm

# ─────────────────────────────────────────────────────────────────
# INSTALL SYSTEM TOOLS (FFmpeg + build tools)
# ─────────────────────────────────────────────────────────────────
# apt-get = Linux package manager (like pip, but for system tools)
# -y = say yes to all prompts automatically (no interactive mode)
# --no-install-recommends = don't install optional extras (keeps image small)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# ↑ rm -rf /var/lib/apt/lists/* = delete package cache after installing
# This saves space in the final image (otherwise the cache stays)

# ─────────────────────────────────────────────────────────────────
# SET WORKING DIRECTORY
# ─────────────────────────────────────────────────────────────────
# WORKDIR = "from now on, all commands run from /app inside the container"
# Like doing: mkdir /app && cd /app
# All COPY, RUN, CMD commands below happen relative to /app
WORKDIR /app

# ─────────────────────────────────────────────────────────────────
# INSTALL PYTHON LIBRARIES
# ─────────────────────────────────────────────────────────────────
# WHY copy requirements.txt BEFORE copying all other code?
# Docker caches each step. If only your code changes (not requirements),
# Docker reuses the cached pip install step — much faster rebuilds!
#
# If we did COPY . . first, any code change would force pip install again.
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir = don't save pip's download cache → smaller image

# ─────────────────────────────────────────────────────────────────
# COPY APPLICATION CODE
# ─────────────────────────────────────────────────────────────────
# COPY source destination
# COPY . .  means: copy everything from current folder (backend/) into /app
# This runs AFTER pip install so code changes don't invalidate pip cache
COPY . .

# ─────────────────────────────────────────────────────────────────
# CREATE TEMP DIRECTORIES
# ─────────────────────────────────────────────────────────────────
# Our app creates temp files during transcoding.
# We create the folders here so they exist when the container starts.
RUN mkdir -p temp_transcoding temp_chunks storage/uploads storage/signatures

# ─────────────────────────────────────────────────────────────────
# EXPOSE PORT
# ─────────────────────────────────────────────────────────────────
# EXPOSE = "this container listens on port 8000"
# This is documentation — it doesn't actually open the port.
# The actual port opening happens in docker-compose (ports: "8000:8000")
EXPOSE 8000

# ─────────────────────────────────────────────────────────────────
# START COMMAND
# ─────────────────────────────────────────────────────────────────
# CMD = what runs when container starts
# ["uvicorn", "app.main:app", ...] = run uvicorn with these arguments
# --host 0.0.0.0 = listen on ALL network interfaces
#   (without this, it only listens on localhost INSIDE the container
#    and nothing outside can reach it)
# --port 8000 = on port 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]