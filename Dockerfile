# ---- 1) compila o React
FROM node:22-alpine AS frontend
WORKDIR /front
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2) imagem final: FastAPI servindo a API e as telas
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /front/dist ./frontend_dist

# usuário sem privilégios; /dados é o volume do banco SQLite
RUN useradd --system --uid 1000 --home /app gestaoaxia \
    && mkdir -p /dados && chown gestaoaxia:gestaoaxia /dados
USER gestaoaxia
VOLUME ["/dados"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/saude', timeout=4)"

# 1 worker: SQLite não ganha nada com vários processos e assim o admin inicial é criado uma vez só
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
