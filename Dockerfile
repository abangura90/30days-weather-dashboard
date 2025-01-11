FROM python:3.11-alpine

RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    aws-cli

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/weather_dashboard.py .

CMD ["python", "weather_dashboard.py"]