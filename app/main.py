from fastapi import FastAPI, HTTPException

app = FastAPI()

def fibonacci_iterative(n: int) -> int:
    if n == 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

@app.get("/v1/fib")
def get_fibonacci(n: int):
    if n < 0:
        raise HTTPException(status_code=400, detail="Input must be a non-negative integer.")
    
    result = fibonacci_iterative(n)
    return {"n": n, "fibonacci": result} 