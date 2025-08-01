import sys
import redis
import hashlib
import math
import time
import os
from fastapi import FastAPI, HTTPException, Response, Header, Request
from pydantic import BaseModel, Field
from typing import Union
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Python messes up on converting huge numbers to strings. Removing the limit here.
sys.set_int_max_str_digits(0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on startup.
    print("Warming up the cache...")
    for i in range(100):
        cache_key = f"fib:{i}"
        # Skip if already exists
        if not redis_client.exists(cache_key):
            # Iterative is fine for small numbers
            result = fibonacci_iterative(i)
            redis_client.setex(cache_key, 86400, str(result))
    print("Cache warmup complete.")
    yield
    # This runs on shutdown.
    print("Shutting down.")


app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

# Rate limit settings
RATE_LIMIT_TOKENS = 100
RATE_LIMIT_WINDOW = 60  # seconds

# Docs helper......
class FibonacciResponse(BaseModel):
    n: int
    fibonacci: Union[int, str] = Field(..., description="The nth Fibonacci number. Large numbers are returned as strings to preserve precision.")

def fibonacci_iterative(n: int) -> int:
    if n == 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

def fibonacci_fast_doubling(n: int) -> int:
    if n == 0:
        return 0
    a, b = 0, 1
    for i in range(n.bit_length() - 1, -1, -1):
        a2 = a * (2 * b - a)
        b2 = a * a + b * b
        if (n >> i) & 1:
            a, b = b2, a2 + b2
        else:
            a, b = a2, b2
    return a

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # We only want to rate limit the /v1/fib endpoint
    if not request.url.path.startswith("/v1/fib"):
        return await call_next(request)

    # In a real app you will have to get the client identifier from an API key or auth token.
    # For this we will just use the host.
    client_id = request.client.host
    bucket_key = f"rate_limit:{client_id}"
    
    # Check if the bucket exists
    if not redis_client.exists(bucket_key):
        # Create a new bucket with full tokens and a 60s expiration
        redis_client.hset(bucket_key, mapping={
            "tokens": RATE_LIMIT_TOKENS,
            "last_refill": int(time.time())
        })
        redis_client.expire(bucket_key, RATE_LIMIT_WINDOW)

    bucket = redis_client.hgetall(bucket_key)
    tokens = float(bucket.get("tokens", RATE_LIMIT_TOKENS))
    last_refill = int(bucket.get("last_refill", int(time.time())))

    # Refill the bucket based on time
    time_since_refill = int(time.time()) - last_refill
    refill_amount = (time_since_refill / RATE_LIMIT_WINDOW) * RATE_LIMIT_TOKENS
    tokens = min(RATE_LIMIT_TOKENS, tokens + refill_amount)
    
    # Get 'n' from query params to calculate request cost
    try:
        n = int(request.query_params.get("n", 1))
        request_cost = 1 + math.floor(math.log10(n + 1))
    except (ValueError, TypeError):
        request_cost = 1 # Default cost for an invalid 'n'

    if tokens < request_cost:
        raise HTTPException(status_code=429, detail="Too Many Requests")

    # Consume tokens
    new_token_count = tokens - request_cost
    redis_client.hset(bucket_key, "tokens", new_token_count)
    
    response = await call_next(request)
    
    # Add rate limit headers to our response
    response.headers["X-RateLimit-Remaining"] = str(int(new_token_count))
    response.headers["X-RateLimit-Cost"] = str(request_cost)
    return response


@app.get(
    "/v1/fib",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "examples": {
                        "small_number": {
                            "summary": "A small number example",
                            "value": {"n": 10, "fibonacci": 55}
                        },
                        "large_number": {
                            "summary": "A large number example (returned as string)",
                            "value": {"n": 95, "fibonacci": "31940434634990099905"}
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid Input",
            "content": {
                "application/json": {
                    "example": {"detail": "Input must be a non-negative integer."}
                }
            }
        },
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "n"],
                                "msg": "value is not a valid integer",
                                "type": "type_error.integer"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def get_fibonacci(n: int, response: Response, if_none_match: str = Header(None)):
    if n < 0:
        raise HTTPException(status_code=400, detail="Input must be a non-negative integer.")

    cache_key = f"fib:{n}"
    cached_result = redis_client.get(cache_key)

    if cached_result:
        etag = hashlib.md5(cached_result.encode()).hexdigest()
        if if_none_match == etag:
            return Response(status_code=304)
        
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "public, immutable, max-age=86400"
        
        # The cached result is always a string so we need to decide if we can convert it back to an int
        if n < 93:
            return {"n": n, "fibonacci": int(cached_result)}
        else:
            return {"n": n, "fibonacci": cached_result}

    start_time = time.perf_counter_ns()
    if n > 92: 
        result = fibonacci_fast_doubling(n)
    else:
        result = fibonacci_iterative(n)
    end_time = time.perf_counter_ns()
    
    compute_time_us = (end_time - start_time) // 1000
    response.headers["X-Compute-us"] = str(compute_time_us)

    result_str = str(result)
    etag = hashlib.md5(result_str.encode()).hexdigest()

    redis_client.setex(cache_key, 86400, result_str) # Cache for 24 hours

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, immutable, max-age=86400"

    # JS can't handle ints this big, so send as a string.
    if n >= 93:
        response.headers["X-Precision"] = "string"
        return {"n": n, "fibonacci": str(result)}
    
    response.headers["X-Precision"] = "integer"
    return {"n": n, "fibonacci": result} 