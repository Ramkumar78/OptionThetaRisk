# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We also install gunicorn for a production-ready WSGI server
RUN pip install --no-cache-dir -r requirements.txt gunicorn

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
# Using 1 worker to avoid potential SQLite locking issues with the background cleanup thread
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "webapp.app:app"]
