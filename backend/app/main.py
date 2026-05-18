from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.health import router as health_router
from app.routes.webhook import router as webhook_router

app = FastAPI(title=settings.app_name)

# Allow the future React dashboard to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "AI SecureWatch backend is running"}


app.include_router(health_router)
app.include_router(webhook_router)
