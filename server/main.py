from fastapi import FastAPI
from router import llm

app = FastAPI()

app.include_router(llm.router)
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}