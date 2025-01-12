FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tests

# Copy all necessary files
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements-qa.txt

# Set environment variables
ENV PYTHONPATH=/tests/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set entry point and default command
ENTRYPOINT ["pytest"]
CMD ["-v", "--cov=weather_collector", "--cov-report=term-missing", "--cov-config=.coveragerc"]