FROM python:3.11-alpine

RUN apk add --no-cache \
    git \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo

WORKDIR /tests

COPY requirements-qa.txt  .
RUN pip install --no-cache-dir -r requirements-qa.txt

ENV PYTHONPATH=/tests/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["pytest"]
CMD ["-v", "--cov=weather_dashboard", "--cov-report=term-missing"]