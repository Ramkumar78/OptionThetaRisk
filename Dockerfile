# Stage 1: Build React Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install system dependencies (optional but good for stability)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# --- THE FIX STARTS HERE ---

# 1. Upgrade pip to ensure better networking handling
RUN pip install --upgrade pip

# 2. Install HEAVY libraries first with a huge timeout
# This prevents one large file failure from ruining the whole build
RUN pip install --default-timeout=1000 --no-cache-dir \
    "numpy>=1.24.0" \
    "pandas>=2.1.4" \
    "pyarrow>=14.0.0" \
    "scipy>=1.10.0"

# 3. Install the rest of the requirements
RUN pip install --default-timeout=1000 --no-cache-dir --pre -r requirements.txt gunicorn

# --- THE FIX ENDS HERE ---

# Copy ONLY backend code
COPY option_auditor ./option_auditor
COPY webapp ./webapp
COPY *.py .

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/webapp/static/react_build

# Environment Config
ENV PYTHONPATH=/app
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Run Gunicorn
CMD sh -c "gunicorn --log-level warning -w ${WEB_CONCURRENCY:-1} --timeout 120 -b 0.0.0.0:${PORT:-5000} webapp.app:app"
