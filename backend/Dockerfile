FROM python:3.11-slim

WORKDIR /app

# System-Abhängigkeiten für psycopg2 (braucht libpq zum Kompilieren, falls
# nicht die -binary-Variante installiert wird — requirements.txt nutzt
# psycopg2-binary, daher hier eigentlich nicht zwingend nötig, aber schadet
# nicht als Absicherung).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Modell-Download passiert beim ersten Request (lazy loading in
# embeddings.py) — kein Vorab-Download im Image nötig, aber der erste
# Request nach jedem Neustart dauert dadurch spürbar länger (Download +
# Laden von e5-base, ca. 20-60s je nach Serveranbindung).
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]