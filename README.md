# Fibonacci API

This is a simple REST API that computes and returns the nth number in the Fibonacci sequence. It's built with Python and FastAPI, and it's designed to be a production-ready service with a focus on observability and security.

## Features

- **Fast & Efficient**: Uses an iterative approach for small numbers and a fast-doubling algorithm for large numbers.
- **Precision Safe**: Returns very large numbers as strings to avoid precision issues in clients like JavaScript.
- **Caching**: Uses Redis to cache results for 24 hours, with ETag support for `304 Not Modified` responses.
- **Rate Limiting**: Implements a complexity-weighted token bucket algorithm to prevent abuse.
- **Cache Warm-up**: Pre-computes the first 100 Fibonacci numbers on startup for instant responses.
- **Observability**: Exposes Prometheus metrics, a pre-configured Grafana dashboard, and Jaeger tracing.
- **Containerized**: Comes with a multi-stage `Dockerfile` and a `docker-compose.yml` for easy local development.
- **CI/CD**: Includes a GitHub Actions workflow for automated testing, security scanning, and smoke tests.

## Running the API

### Prerequisites

- Docker and Docker Compose

### Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd fibonacci-api
    ```

2.  **Start the services:**
    ```bash
    make compose-up
    ```

3.  **Send a request:**
    ```bash
    curl "http://localhost:8000/v1/fib?n=10"
    ```

## Observability Quick Demo

1.  **Start the stack:**
    ```bash
    make compose-up
    ```

2.  **Generate some traffic:**
    ```bash
    curl "http://localhost:8000/v1/fib?n=10"
    curl "http://localhost:8000/v1/fib?n=50"
    curl "http://localhost:8000/v1/fib?n=100"
    ```

3.  **View the metrics:**
    - **Prometheus:** http://localhost:9090
    - **Grafana:** http://localhost:3000 (admin/admin)
    - **Jaeger:** http://localhost:16686 