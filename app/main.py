from fastapi import FastAPI

from app.config import settings


app = FastAPI(title="SEELE Review FastAPI", version="0.1.0")

if "gitlab" in settings.repo_targets:
    from app.routers import gitlab
    app.include_router(gitlab.router)

if "github" in settings.repo_targets:
    from app.routers import github
    app.include_router(github.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "SEELE Review API is running"}
