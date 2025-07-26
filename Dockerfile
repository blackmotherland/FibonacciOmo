# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies and upgrade setuptools for security
RUN pip install --upgrade pip setuptools>=78.1.1

# Copy and install requirements (setuptools is explicitly listed first)
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy built wheels from the builder stage
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .

# Install packages including upgraded setuptools
RUN pip install --upgrade pip && \
    pip install --no-index --find-links=/wheels -r requirements.txt

# Copy application code
COPY ./app /app

# Set the python path
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app"] 