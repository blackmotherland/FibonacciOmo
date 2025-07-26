import sys
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Union

# Python chokes on converting huge numbers to strings. This removes the limit.
sys.set_int_max_str_digits(0)

app = FastAPI()

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
def get_fibonacci(n: int, response: Response):
    if n < 0:
        raise HTTPException(status_code=400, detail="Input must be a non-negative integer.")
    
    if n > 92: 
        result = fibonacci_fast_doubling(n)
    else:
        result = fibonacci_iterative(n)

    # JS can't handle ints this big, so send as a string.
    if n >= 93:
        response.headers["X-Precision"] = "string"
        return {"n": n, "fibonacci": str(result)}
    
    response.headers["X-Precision"] = "integer"
    return {"n": n, "fibonacci": result} 