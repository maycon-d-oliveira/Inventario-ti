FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000
ENV FLASK_DEBUG=0

WORKDIR /app

COPY requirements.txt /app/

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        default-jre && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o driver JDBC do OpenEdge (coloque o arquivo openedge.jar na raiz do projeto)
COPY openedge.jar /app/openedge.jar
ENV OPENEDGE_JAR=/app/openedge.jar

COPY . .

EXPOSE 5000

RUN chmod +x entrypoint.sh
CMD ["python", "app.py"]
