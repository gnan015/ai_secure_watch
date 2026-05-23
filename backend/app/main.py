from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.detections import router as detections_router
from app.routes.discord_webhooks import router as discord_webhooks_router
from app.routes.github_app import router as github_app_router
from app.routes.health import router as health_router
from app.routes.repositories import router as repositories_router
from app.routes.v2_dashboard import router as v2_dashboard_router
from app.routes.webhook import router as webhook_router

app = FastAPI(title=settings.app_name)

# Allow the React dashboard to call this API. In production, set FRONTEND_URL
# to the deployed Vercel dashboard URL.
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
app.include_router(detections_router, prefix="/api")
app.include_router(github_app_router, prefix="/api")
app.include_router(repositories_router, prefix="/api")
app.include_router(discord_webhooks_router, prefix="/api")
app.include_router(v2_dashboard_router, prefix="/api")
