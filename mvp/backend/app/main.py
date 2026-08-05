from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app import cache, db_models  # noqa: F401 -- import registers models on Base.metadata
from app.db import Base, engine, run_migrations
from app.routers import auth_router, family_router
from app.services.context_engine import PersonNotFound, build_profile
from app.services.llm_client import LLMNotConfigured, LLMRequestFailed

Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(title="Human Context AI — MVP")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.include_router(auth_router.router)
app.include_router(family_router.router)


@app.get("/api/person/{name}")
async def get_person(name: str):
    cached = cache.get(name)
    if cached:
        return cached

    try:
        profile = await build_profile(name)
    except PersonNotFound:
        raise HTTPException(status_code=404, detail=f"No public figure found for '{name}'.")
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except LLMRequestFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    data = profile.model_dump(mode="json")
    cache.put(name, data)
    return data


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
