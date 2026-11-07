# Obraz backendu: Python 3.13 w wersji "slim" (mniejszy obraz, bez zbędnych narzędzi).
FROM python:3.13-slim

# Brak plików .pyc i niebuforowane logi (od razu widoczne w `docker compose logs`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Najpierw same zależności: ta warstwa obrazu jest cache'owana i nie przebudowuje się
# przy każdej zmianie kodu, tylko przy zmianie requirements.txt.
# Plik zależności wybiera docker-compose.yml: w trybie deweloperskim dochodzą pytest i ruff.
ARG REQUIREMENTS=requirements.txt
# Tryb deweloperski: czcionka z polskimi znakami dla sztucznych wyciągów PDF w testach.
RUN if [ "$REQUIREMENTS" = "requirements-dev.txt" ]; then \
      apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
      && rm -rf /var/lib/apt/lists/*; \
    fi
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r ${REQUIREMENTS}

COPY . .

# Aplikacja nie działa jako root (dobra praktyka bezpieczeństwa kontenerów).
RUN useradd --create-home --uid 1000 appuser
# Katalog na klucz JWT. Właściciela dziedziczy po nim wolumen z docker-compose.yml.
RUN mkdir /data && chown appuser:appuser /data
USER appuser

EXPOSE 8000

CMD ["sh", "start.sh"]
