FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy pyproject.toml, parse and install dependencies using standard pip
COPY pyproject.toml .
RUN python -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print('\n'.join(data['project']['dependencies']))" > requirements.txt \
    && pip install --default-timeout=3000 --retries 10 --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --default-timeout=3000 --retries 10 --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port
EXPOSE 8000

# Run alembic migrations and then start uvicorn server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
