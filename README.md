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

## Operational Considerations

(how I’d run this, in real life, with what I know works)

### Container stuff

So first off, I package the app using a two-stage Dockerfile. The builder stage installs dependencies, compiles wheels, all that stuff. The final image is clean and tiny—it’s just Python and the app. I always run containers as a non-root user and lock the filesystem to read-only. That combo just makes life easier long-term, especially when you’re running in Kubernetes.

Nothing sensitive gets baked into the image—config and secrets get passed in when the container starts, like they should be.

For deploying, I usually stick with Helm. I keep it light—just a simple values file and some templates—and I use helm upgrade --atomic so that if anything breaks during the rollout, it’ll automatically roll back before I even have to look at it.

### CI/CD, the way I like it

When I push code, GitHub Actions kicks off a bunch of things:
	•	I’ve got linters and formatters in pre-commit, along with mypy for types and gitleaks to make sure no one accidentally pushes secrets.
	•	Then I run tests. They’re quick and cover both small stuff and the full request flow. I care more about catching edge cases than chasing 100% coverage, but it’s usually pretty high.
	•	Then there’s a supply-chain step: we generate an SBOM and check for CVEs, and I check licenses just to stay ahead of any surprises.
	•	After that, the container gets built with BuildKit and signed with Cosign. This way, we know exactly what’s been built and that it hasn’t been tampered with.
	•	Once the image is built, I do a quick smoke test. I spin up the container, hit it with a known request, and make sure things like caching work and the warm-up logic has done its job.
	•	Argo CD watches the Helm chart. When the image tag changes, it automatically deploys to staging and then to production. If it notices a problem—like pods failing probes—it reverts to the last good version. No manual steps. No firefighting.

### Observability & logs

For metrics, I track request latency and cache-hit rates. I let Prometheus scrape those every 15 seconds—it gives me enough resolution to catch issues without flooding the system.

In Grafana, I auto-load a simple dashboard with latency and error rate. It’s nothing flashy, just enough to let me know how the service is behaving without clicking through menus.

For traces, I use OpenTelemetry’s FastAPI middleware, which makes it easy to track what’s happening inside the app. I keep sampling light—around 10%—so we get enough visibility without flooding Jaeger with data.

Logs are structured with structlog, and they include things like request ID, status code, how long the Fibonacci calculation took, and so on. Fluent Bit picks those up and ships them to Loki. We keep logs hot for about a week, then archive them to S3. That setup gives us plenty of room for debugging without worrying about costs piling up.

And of course, I’ve got a Prometheus alert wired up to fire if p95 latency starts creeping above what I expect. That alert goes through PagerDuty and gets the right person paged fast.

### Scaling & staying reliable

This service is stateless, so scaling it is easy. Kubernetes handles scaling pods up and down based on CPU or latency. I usually set it up so the app starts with one pod and scales up as needed. Nothing fancy.

Redis is the one stateful piece. I run it in cluster mode with a few masters and replicas. When memory gets tight, the cluster adds more shards. I’ve found that works well for apps like this where usage can spike based on a few common inputs.

To avoid abuse, I’ve built the rate limiter to be smarter than just requests-per-minute. Instead, it takes into account how expensive each call is. So n=5 costs almost nothing, but n=10 million costs a lot more. Each API key has a token bucket, and if you use up your budget, you get a 429. There’s a cap on how much a single client can use per minute, so no one can hog resources.

Also, when the app starts up, it pre-calculates and caches the Fibonacci values from n=0 to n=99. These are the most common ones you’ll see in the wild. It helps a lot with cold starts and makes sure those first few requests feel fast.

Because the output for any given n is always the same, I use ETag headers and mark the response as immutable. That way, if you put this behind a CDN or a company reverse proxy, you get cache hits automatically without needing extra logic.

### Rollbacks & recovery

For rollbacks, I lean on Helm’s built-in rollback mechanism. If something goes wrong during a deploy, it’ll just revert to the last working version. It works well and takes a lot of pressure off during rollouts.

Redis gets backed up regularly. We snapshot it overnight and keep daily and weekly backups. If something goes wrong and we need to restore, we can go back to any of those points and pick up without a full rebuild.

This is how I’d actually run this in production. 