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

# torch explizit als CPU-only-Build installieren, BEVOR requirements.txt
# (die transitiv sentence-transformers -> torch zieht). Ohne diesen Schritt
# lädt pip automatisch die volle CUDA-GPU-Variante von torch (~2-3GB an
# nvidia-*-Paketen wie cudnn, cublas, nccl) — auf einem Server ohne GPU
# komplett unnötig und hat beim ersten Versuch den Server-Speicher gesprengt.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Modell-Download passiert beim ersten Request (lazy loading in
# embeddings.py) — kein Vorab-Download im Image nötig, aber der erste
# Request nach jedem Neustart dauert dadurch spürbar länger (Download +
# Laden von e5-base, ca. 20-60s je nach Serveranbindung).
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]