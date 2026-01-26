from fastapi import FastAPI

app = FastAPI(title="FastAPI Starter")

@app.get("/")
def read_root():
    return {"ok": True, "msg": "Hello from FastAPI"}
