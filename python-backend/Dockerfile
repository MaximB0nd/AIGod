FROM python:3.13-slim

WORKDIR /app

# chromadb/hnswlib требуют C++ — в slim нет компилятора; отключаем нативную сборку
ENV HNSWLIB_NO_NATIVE=1

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Код приложения
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
