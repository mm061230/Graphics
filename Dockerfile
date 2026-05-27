FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        inkscape \
        tesseract-ocr \
        tesseract-ocr-chi-sim \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY core ./core
COPY config ./config
COPY run_task.py ./
COPY tests ./tests

RUN pip install -e .

CMD ["python", "run_task.py", "--help"]

