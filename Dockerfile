# [Stage 1: Frontend - Standard Build]
FROM node:20.11-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# [Stage 2: Backend - Robust Build]
FROM python:3.12-slim
# Set work directory
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc git ca-certificates curl unzip \
    && rm -rf /var/lib/apt/lists/*

# 2. Upgrade PIP (Vital for better networking handling)
RUN pip install --upgrade pip

# Copy requirements file
COPY requirements.txt .

# 3. INSTALL HEAVY LIBRARIES FIRST (With 1000s Timeout)
# We install these separately so if one fails, we don't restart the whole build.
# This fixes the "ReadTimeoutError" on slow connections.
RUN pip install --default-timeout=1000 --no-cache-dir \
    "numpy>=1.24.0" \
    "pandas>=2.1.4" \
    "scipy>=1.10.0" \
    "pyarrow>=14.0.0"

# 4. Install the rest of the requirements
# We use --pre for pandas-ta compatibility
RUN pip install --default-timeout=1000 --no-cache-dir --pre -r requirements.txt gunicorn

# 5. Copy Backend Code
COPY option_auditor ./option_auditor
COPY webapp ./webapp
COPY *.py .

# 6. Copy Built Frontend Assets
COPY --from=frontend-builder /app/frontend/dist /app/webapp/static/react_build

# 7. Setup Environment
ENV PYTHONPATH=/app
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# 8. Run Application
CMD sh -c "gunicorn --log-level warning -w 1 --timeout 120 -b 0.0.0.0:${PORT:-5000} webapp.app:app"
