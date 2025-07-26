# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY ./app /app


# Stage 2: Runtime - using a minimal distroless image
FROM gcr.io/distroless/python3-debian12

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
# Copy the application code
COPY --from=builder /app /app

WORKDIR /app

# Set the PATH to include the venv's bin directory
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 