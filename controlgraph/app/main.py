
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app import models  # noqa: F401
from app.routers import health, auth, data_assets, governance, lineage, controls, exceptions, approvals, evidence, webhooks, dashboard


settings = get_settings()
app = FastAPI(title=settings.APP_NAME)

origins = ["*"] if settings.CORS_ORIGINS == "*" else [x.strip() for x in settings.CORS_ORIGINS.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(data_assets.router)
app.include_router(governance.router)
app.include_router(lineage.router)
app.include_router(controls.router)
app.include_router(exceptions.router)
app.include_router(approvals.router)
app.include_router(evidence.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
