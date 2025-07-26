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