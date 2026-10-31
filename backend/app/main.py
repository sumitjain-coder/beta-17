"""KitchenSync FastAPI entrypoint (owner: Role 4).

Routers are registered defensively: if a teammate's router file is not
pushed yet, the app still starts and logs a warning. This keeps main runnable.
"""
import importlib
import logging
import os
from app.db import Base, engine
from app import models
from fastapi.responses import JSONResponse
from sqlalchemy import text

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
log = logging.getLogger("kitchensync")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="KitchenSync API", version="0.1.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# module name in app/routers -> owner (for log messages)
ROUTERS = {
    "stock": "Role 1",
    "recipes": "Role 2",
    "planner": "Role 2",
    "suggestions": "Role 2",
    "shopping": "Role 4",
    "audit": "Role 4",
}

for name, owner in ROUTERS.items():
    try:
        module = importlib.import_module(f"app.routers.{name}")
        app.include_router(module.router)
        log.info("router '%s' registered", name)
    except ModuleNotFoundError:
        log.warning("router '%s' not found yet (owner: %s) - skipped", name, owner)
    except Exception as exc:  # a broken router must not take the whole app down
        log.error("router '%s' failed to load: %s", name, exc)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/db")
def health_db():
    """Check whether the backend can reach MySQL."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        log.error("Database health check failed: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unreachable",
                "error": type(exc).__name__,
            },
        )
    
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    log.info("Database tables created/verified")
