from fastapi import FastAPI
from router import llm, agv

app = FastAPI()

app.include_router(llm.router)
app.include_router(agv.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}