# Stage 1: Tailwind CSS Build
FROM node:22-alpine AS css-builder
WORKDIR /build
COPY package.json ./
RUN npm install
COPY tailwind.config.js ./
COPY app/static/input.css ./app/static/
COPY app/static/index.html ./app/static/
RUN npm run build:css

# Stage 2: Python Runtime
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gebautes CSS einbinden (überschreibt leere Platzhalterdatei)
COPY --from=css-builder /build/app/static/output.css ./app/static/output.css

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
