from fastapi import FastAPI
from .api.endpoints import router as hwpx_router
from .core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME, description="HWPX Editor Tools for AI Agents", version="3.0.0"
)

app.include_router(hwpx_router, prefix="/api/v1/hwpx", tags=["hwpx"])


@app.get("/")
def root():
    return {"message": "Welcome to HWPX Editor API"}
