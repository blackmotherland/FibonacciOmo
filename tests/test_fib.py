from fastapi.testclient import TestClient
from app.main import app
import hashlib
from unittest.mock import patch

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