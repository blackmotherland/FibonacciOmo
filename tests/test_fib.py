from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_fibonacci_endpoint():
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

def test_fibonacci_precision_fallback():
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

def test_fibonacci_large_n():
    # Test a really big number.
    response = client.get("/v1/fib?n=100000")
    assert response.status_code == 200
    assert response.headers["X-Precision"] == "string"
    data = response.json()
    assert data["n"] == 100000
    assert isinstance(data["fibonacci"], str)
    # Just check it's a long string.
    assert len(data["fibonacci"]) > 20000 