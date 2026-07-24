"""CODReal FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    auth_router,
    campaigns,
    dashboard,
    demo,
    health,
    integrations,
    jobs,
    matching,
    orders,
    users,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "CODReal API — Real ROAS & Profit for COD e-commerce (Morocco). "
        "Ingestion → Matching → Calculation → Presentation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_prefix
app.include_router(health.router, prefix=prefix)
app.include_router(demo.router, prefix=prefix)  # local demo: /demo/ready, /demo/run
app.include_router(auth_router.router, prefix=prefix)
app.include_router(orders.router, prefix=prefix)
app.include_router(campaigns.router, prefix=prefix)
app.include_router(matching.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(integrations.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{prefix}/health",
        "demo_ready": f"{prefix}/demo/ready",
        "demo_run": f"POST {prefix}/demo/run",
        "local_demo_guide": "docs/LOCAL_DEMO.md",
    }
