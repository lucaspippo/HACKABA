# P22·C — PolPilot DEMO para Render: UN solo servicio, UN solo puerto.
# SOLO el tenant demo viaja: data/ (piloto Horizonte), credenciales y .env
# quedan afuera por .dockerignore Y se verifica acá adentro (el build FALLA
# si algo del piloto se cuela — ver el RUN de guardia más abajo).

# --- Etapa 1: el frontend compilado (Vite) -----------------------------------
FROM node:20-slim AS front
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Etapa 2: el runtime (Python + WeasyPrint en Linux) ----------------------
FROM python:3.12-slim
# Las libs de sistema que WeasyPrint necesita en Linux (el PDF se genera en el server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libcairo2 \
    libgdk-pixbuf-2.0-0 libffi-dev libharfbuzz0b libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY data-demo/ data-demo/
COPY deploy/ deploy/
COPY --from=front /build/dist frontend/dist

# GUARDIA DE PRIVACIDAD: el build FALLA si los datos del piloto o un .env
# llegaron a la imagen (defensa en profundidad sobre el .dockerignore).
# P37 — se reforzó tras el incidente del logo del piloto: la guarda vieja solo
# miraba .env/credenciales/data/ y NUNCA inspeccionaba el bundle del frontend,
# por eso no detectó piloto.png ni los datos del piloto embebidos en el JS.
# Ahora falla si el ASSET o el NOMBRE/DATOS del piloto aparecen en cualquier
# archivo servido (incluido frontend/dist, el bundle público de la demo).
RUN test ! -e /app/data && \
    test ! -e /app/backend/.env && \
    test ! -e /app/backend/credenciales.json && \
    test ! -e /app/data-demo/credenciales.json && \
    if find /app -name "*.env" -o -name "credenciales.json" | grep -q .; then \
      echo "GUARDIA: archivo sensible en la imagen" && exit 1; fi && \
    if find /app -iname "piloto.*" | grep -q .; then \
      echo "GUARDIA: asset del piloto (piloto.*) en la imagen" && exit 1; fi && \
    if grep -rilE "Supermercados Horizonte|piloto\.(png|jpg|jpeg|svg)" /app/frontend/dist 2>/dev/null | grep -q .; then \
      echo "GUARDIA: nombre/asset/datos del piloto en el bundle servido (frontend/dist)" && exit 1; fi && \
    echo "guardia de privacidad: OK (sin asset ni datos del piloto en la demo)"

# Image-wide layout only. Everything tenant- or demo-specific lives in the
# service's envVars (see render.yaml): this image is built once and must be
# usable by any tenant. It used to bake in the tenant slug and the demo
# switches, which meant a productive service built from this image came up
# autologged-in as the tenant owner unless every one of them was overridden
# by hand — silently. tests/test_deploy_config.py now asserts none of those
# names appear in this file at all, comments included, so do not name them
# here even to explain them.
ENV POLPILOT_CANONICAL_DIR=/app/canonical \
    POLPILOT_STATIC_DIR=/app/frontend/dist \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["python", "deploy/boot.py"]
