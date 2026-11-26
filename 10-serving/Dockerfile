# Build from the repo root:  docker build -f 10-serving/Dockerfile -t helpdesk-api .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Install dependencies first so this layer is cached when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY 10-serving ./10-serving

# Don't run as root
RUN useradd --create-home agent && chown -R agent /app
USER agent

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app:app", "--app-dir", "10-serving", "--host", "0.0.0.0", "--port", "8000"]
