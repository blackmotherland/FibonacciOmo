import sys
import redis
import hashlib
from fastapi import FastAPI, HTTPException, Response, Header
from pydantic import BaseModel, Field
from typing import Union

# Python chokes on converting huge numbers to strings. This removes the limit.
sys.set_int_max_str_digits(0)

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Docs helper.
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

@app.get("/v1/fib")
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
        
        # The cached result is always a string, so we need to decide if we can convert it back to an int.
        if n < 93:
            return {"n": n, "fibonacci": int(cached_result)}
        else:
            return {"n": n, "fibonacci": cached_result}

    if n > 92: 
        result = fibonacci_fast_doubling(n)
    else:
        result = fibonacci_iterative(n)
    
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