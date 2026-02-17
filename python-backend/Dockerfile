FROM python:3.13-slim

WORKDIR /app

# API без chromadb (для LLM с памятью добавь chromadb в requirements-docker.txt)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Код приложения
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
