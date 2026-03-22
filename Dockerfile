FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install uv

RUN uv sync

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "page_analyzer:app"]