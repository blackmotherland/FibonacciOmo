from fastapi.testclient import TestClient
from app.main import app
import hashlib
from unittest.mock import patch
import unittest
import time
import pytest
from fastapi import HTTPException

client = TestClient(app)

# Since we're now depending on Redis, we'll mock it for most tests
# to keep them fast and independent of a running Redis instance.
@patch('app.main.redis_client')
def test_fibonacci_endpoint(mock_redis):
    mock_redis.get.return_value = None # Ensure no cache hit

    # Test case for n = 2, expecting F(2) = 1
    response = client.get("/v1/fib?n=2")
    assert response.status_code == 200
    assert response.json() == {"n": 2, "fibonacci": 1}

    # Test case for n = 10, expecting F(10) = 55
    response = client.get("/v1/fib?n=10")
    assert response.status_code == 200
    assert response.json() == {"n": 10, "fibonacci": 55}

    # Test case for n = 0
    response = client.get("/v1/fib?n=0")
    assert response.status_code == 200
    assert response.json() == {"n": 0, "fibonacci": 0}

    # Test case for n = 1
    response = client.get("/v1/fib?n=1")
    assert response.status_code == 200
    assert response.json() == {"n": 1, "fibonacci": 1}

    # Test case for negative input
    response = client.get("/v1/fib?n=-1")
    assert response.status_code == 400
    assert response.json() == {"detail": "Input must be a non-negative integer."}

@patch('app.main.redis_client')
def test_fibonacci_precision_fallback(mock_redis):
    mock_redis.get.return_value = None

    # n=92 should be a number.
    response = client.get("/v1/fib?n=92")
    assert response.status_code == 200
    assert response.headers["X-Precision"] == "integer"
    data = response.json()
    assert data["n"] == 92
    assert isinstance(data["fibonacci"], int)
    assert data["fibonacci"] == 7540113804746346429

    # n=93 should be a string.
    response = client.get("/v1/fib?n=93")
    assert response.status_code == 200
    assert response.headers["X-Precision"] == "string"
    data = response.json()
    assert data["fibonacci"] == "12200160415121876738"

@patch('app.main.redis_client')
def test_fibonacci_large_n(mock_redis):
    mock_redis.get.return_value = None

    # Test a really big number.
    response = client.get("/v1/fib?n=100000")
    assert response.status_code == 200
    assert response.headers["X-Precision"] == "string"
    data = response.json()
    assert data["n"] == 100000
    assert isinstance(data["fibonacci"], str)
    # Just check it's a long string.
    assert len(data["fibonacci"]) > 20000

@patch('app.main.redis_client')
def test_cache_hit_and_etag(mock_redis):
    # Simulate a cached value
    n = 50
    result = "12586269025"
    etag = hashlib.md5(result.encode()).hexdigest()
    
    mock_redis.get.return_value = result

    # First request should be a cache hit
    response = client.get(f"/v1/fib?n={n}")
    assert response.status_code == 200
    assert response.headers["ETag"] == etag
    assert response.json()["fibonacci"] == int(result)

    # Second request with the correct ETag should get a 304
    response = client.get(f"/v1/fib?n={n}", headers={"If-None-Match": etag})
    assert response.status_code == 304

@patch('app.main.redis_client')
def test_cache_miss(mock_redis):
    n = 60
    # Simulate a cache miss
    mock_redis.get.return_value = None
    
    response = client.get(f"/v1/fib?n={n}")
    assert response.status_code == 200
    
    # Verify that the value was set in the cache
    mock_redis.setex.assert_called_once()
    args, _ = mock_redis.setex.call_args
    assert args[0] == f"fib:{n}" # key
    assert args[1] == 86400      # ttl
    assert isinstance(args[2], str) # value

@patch('app.main.redis_client')
def test_rate_limiter(mock_redis):
    client_host = "testclient" # TestClient's default host is 'testclient'
    bucket_key = f"rate_limit:{client_host}"

    # First request, bucket doesn't exist yet, and it's a cache miss.
    mock_redis.exists.return_value = False
    mock_redis.get.return_value = None
    mock_redis.hgetall.return_value = {} # Empty bucket initially

    response = client.get("/v1/fib?n=10")
    assert response.status_code == 200
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Cost" in response.headers
    
    # Check that a new bucket was created
    mock_redis.hset.assert_any_call(bucket_key, mapping={
        "tokens": 100,
        "last_refill": unittest.mock.ANY
    })

    # Subsequent request, consume tokens
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = None # Still a cache miss for the underlying fib call
    mock_redis.hgetall.return_value = {"tokens": "98", "last_refill": str(int(time.time()))}

    response = client.get("/v1/fib?n=1000")
    assert response.status_code == 200
    # Cost for n=1000 is 1 + floor(log10(1001)) = 1 + 3 = 4
    # 98 - 4 = 94 remaining
    assert response.headers["X-RateLimit-Remaining"] == "94"
    assert response.headers["X-RateLimit-Cost"] == "4"

    # Request that exceeds token limit
    mock_redis.get.return_value = None # Still a cache miss
    mock_redis.hgetall.return_value = {"tokens": "1", "last_refill": str(int(time.time()))}
    with pytest.raises(HTTPException) as excinfo:
        client.get("/v1/fib?n=1000") # costs 4 tokens
    assert excinfo.value.status_code == 429

# The TestClient will trigger the lifespan events.
# We can use this to test the cache warmup.
@patch('app.main.redis_client')
def test_cache_warmup(mock_redis):
    # Simulate that the keys don't exist yet.
    mock_redis.exists.return_value = False

    # When the TestClient is created, the startup event fires.
    with TestClient(app) as client:
        # Check that setex was called for all numbers from 0 to 99.
        assert mock_redis.setex.call_count == 100
        # A quick check on one of the calls to make sure it's correct.
        mock_redis.setex.assert_any_call(f"fib:42", 86400, str(267914296))

@patch('app.main.redis_client')
def test_compute_time_header(mock_redis):
    mock_redis.get.return_value = None # cache miss

    response = client.get("/v1/fib?n=50")
    assert response.status_code == 200
    assert "X-Compute-us" in response.headers
    # The time should be a positive integer.
    assert int(response.headers["X-Compute-us"]) >= 0 