# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install build dependencies and upgrade setuptools for security
RUN pip install --upgrade pip && \
    pip install --upgrade setuptools>=78.1.1 && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Remove vulnerable distro setuptools and clean apt cache
RUN apt-get update && \
    apt-get purge -y python3-setuptools && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy built wheels and requirements from the builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install packages including upgraded setuptools
RUN pip install --upgrade pip && \
    pip install --no-index --find-links=/wheels -r requirements.txt && \
    pip install --no-cache-dir --upgrade "setuptools>=80.0.0"

# Copy application code
COPY ./app /app

# Set the python path
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app"] 