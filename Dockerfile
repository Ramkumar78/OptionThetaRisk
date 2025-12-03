# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We also install gunicorn for a production-ready WSGI server
# Use --pre to allow installation of pre-release versions (required for pandas_ta)
RUN pip install --no-cache-dir --pre -r requirements.txt gunicorn

# Copy the current directory contents into the container at /app
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=5000
# Ensure output is sent directly to terminal (avoids buffering issues)
ENV PYTHONUNBUFFERED=1

# Expose the port the app runs on
EXPOSE 5000

# Run the application using Gunicorn
# Use WEB_CONCURRENCY env var for workers, default to 1 for safety with SQLite
# Increased timeout to 120s to prevent screener timeouts
CMD sh -c "gunicorn -w ${WEB_CONCURRENCY:-1} --timeout 120 -b 0.0.0.0:${PORT:-5000} webapp.app:app"
