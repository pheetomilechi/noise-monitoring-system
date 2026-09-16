FROM python:3.11-slim

WORKDIR /app

# Copy both backend and frontend directories
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Install backend dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "backend.app:app"]