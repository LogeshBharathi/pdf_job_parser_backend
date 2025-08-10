from fastapi import FastAPI
from app.api.v1.routes import router

app = FastAPI(title="PDF Job Parser API", version="1.0.0")

app.include_router(router, prefix="/api/v1")
