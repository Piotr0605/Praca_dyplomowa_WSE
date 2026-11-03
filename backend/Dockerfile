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
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Aplikacja nie działa jako root (dobra praktyka bezpieczeństwa kontenerów).
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
