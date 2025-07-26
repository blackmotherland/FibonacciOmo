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

## Testing the API

To run the full suite of unit and integration tests, use the following command:

```bash
make test
```

This will run all the tests in the `tests/` directory and verify that the core logic, caching, and other features are working correctly.

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

## Operational Considerations

(how I’d take this from a take-home project to something I’d trust in a real production environment)

### What’s been delivered

This assessment includes a complete working version of the Fibonacci API with the core functionality in place. You can run it locally, run the tests, see caching work, and even inspect request headers like ETag and response cost. The rate limiting works. The warm-up logic is in place. It includes the metrics endpoint and basic tracing hooks. It is self-contained and deployable to a dev environment.

So for a three-hour scoped exercise, this gives a lot. You can run it, poke it, and see the logic work. The code is tested, and the container builds cleanly. There’s also enough observability that you would know if something broke.

### What this does not include (and what we’d need in production)

While it is solid as a scoped deliverable, this is not production-hardened. It is not battle-tested for high load, not ready for continuous deployment pipelines, and not built out for platform integration at scale. But here’s how I would take it there.

---

### What “Operational Considerations” means to me

When I talk about operational considerations, I mean the set of decisions that let a service not only run but run consistently, scale safely, recover quickly when it breaks, and keep teams sane while doing it. So for me, this includes the container build and security, the way CI and deployment are structured, how we monitor and alert, how logs and metrics are wired in, and how we think about scaling both the app and the dependencies underneath it.

---

### Containerization

This service runs in a clean two-stage container. For production, I would take that a bit further. I would pin all dependencies tightly to reduce the surface for security issues. I would also sign the container with something like Cosign so that we are always deploying known, verified images. I would lock the container to a non-root user and run it with a read-only root filesystem. I do that by default for all services unless they need write access, which this does not.

Everything would be passed in at runtime—no credentials in the image ever. The final container would be built in CI and pushed to a hardened internal registry with policies in place to reject unsigned or unscanned images.

---

### CI and delivery

The CI pipeline in this repo is basic, but in a real setup I would go beyond just testing and linting.

The first thing is that the test suite would run inside the actual container. That removes a whole class of “but it worked locally” problems. We would also have static analysis, type checking, secret scanning, and so on, running in pre-commit and CI.

Every image would get scanned for vulnerabilities and include a software bill of materials that describes what went into it. Once the image is built and signed, I would push it to a registry and then trigger deployment.

I like to use Argo CD for deployment. I set it up so it watches a Helm chart in Git, and when that changes, it syncs the change to staging. If staging looks good, it syncs it to production. If the rollout fails at any step—pods crashing, failing probes, whatever—Argo just reverts to the last known good version.

It is zero-touch after it is set up, and it is saved me more than once.

---

### Monitoring, logs, and visibility

This is something I always think about early, because it is usually what people miss.

Metrics would be sent to Prometheus. I would track request latency, error rate, and cache-hit ratio. That gives me a solid baseline for how the service is doing. I would also expose those metrics with labels so I can slice by route or response type later if I need to.

For tracing, I would use OpenTelemetry. FastAPI has good support for that. I usually set sampling to about ten percent in production so I get just enough to investigate issues without drowning the backend. Traces would go to something like Jaeger or whatever the team is using already.

Logs are JSON and structured. I use structlog for that. The logs include request ID, route, latency, and whatever else we need to troubleshoot. I forward logs with Fluent Bit to Loki or whatever log store is already in place. I usually keep logs hot for a few days and then archive the rest. That’s saved me during incidents plenty of times.

And finally, alerting. I like to set a threshold on p95 latency and fire an alert if it stays above that line for a few minutes. That catches most issues before users start yelling. And of course that alert goes to PagerDuty or whoever is on-call.

---

### Scaling and high traffic

Let me be clear—this is not a service built for high scale out of the box. But it can be.

The app itself is stateless, which makes it very easy to scale horizontally. I would put an HPA in place that scales based on CPU or latency. If you see the average p95 latency creeping up, you add a few pods.

The real bottleneck at scale is Redis. In production, I would run it clustered with shards and replicas. I would watch memory usage closely, and if it starts climbing, I would scale out or tune eviction policies depending on the access pattern.

To protect against abuse, especially from people calling massive Fibonacci numbers, I use a complexity-aware rate limit. That means each request costs more based on the size of n. You only get a fixed budget per minute. I cap that budget so no one client can overrun the service. That system has worked well for me in real environments.

I also pre-populate the most common requests—like n = 0 to n = 99—on startup so those hit the cache right away. For values that never change, I cache them at the edge with immutable headers and ETags. That lets something like Fastly or Cloudflare serve them directly without hitting the origin.

This lets the app scale way beyond what it looks like at first glance. Most real-world traffic hits the same handful of numbers over and over.

---

### Rollbacks and recovery

I lean on Helm’s built-in rollback when something fails during deployment. It is reliable and automatic. I have seen it revert a broken rollout mid-flight and save the team a lot of stress.

For Redis, I snapshot overnight. I keep a handful of daily and weekly backups. Restoring from those is something I test every once in a a while, just to make sure I still know how. You should never be figuring that out for the first time during a real incident.

---

### Wrapping it up

This service, as it stands, is solid for an assessment. It is clean, tested, traceable, and reasonably observable. But if I were taking this to production, I would harden the pipeline, wrap it in stronger deployment safety nets, and put real observability in place.

For me, operational considerations are not just about making things run. They are about making things boring—because boring means stable, predictable, and safe. When I build systems like this, I want the team to be able to sleep through the night. That’s always the goal. 