from fastapi import FastAPI
from app.api.v1 import events, recommend

app = FastAPI(title="Aira Data Project API", version="1.0.0")

app.include_router(events.router, prefix="/api/v1")
app.include_router(recommend.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
