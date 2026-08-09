# ============================================
# BASE IMAGE
# ============================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ============================================
# SYSTEM DEPENDENCIES
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-noto-core \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fontconfig \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv
# ============================================
# CUSTOM FONTS (for certificates)
# Copy your custom fonts if you have Cinzel, Inter, etc.
# ============================================
# COPY ./fonts/ /usr/share/fonts/truetype/custom/
# RUN fc-cache -fv

# ============================================
# PYTHON DEPENDENCIES
# ============================================
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# APPLICATION
# ============================================
COPY . .

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser \
    && chown -R appuser:appgroup /app
USER appuser

# Collect static files during build (optional, for production)
# RUN python manage.py collectstatic --noinput

EXPOSE 8000

# ============================================
# HEALTHCHECK
# ============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# ============================================
# DEFAULT COMMAND (Django development server)
# For production use gunicorn/runbolt behind reverse proxy
# ============================================
CMD ["python", "manage.py", "runbolt", "--host", "0.0.0.0", "--port", "8000", "--processes", "4"]