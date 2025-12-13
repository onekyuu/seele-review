from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.loader import DynamicLoader


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: startup and shutdown logic
    """
    print("\n" + "="*60)
    print("🤖 Seele Review Starting...")
    print("="*60)

    loader = DynamicLoader(app)
    loader.load_all()

    print(f"\n📋 Configuration:")
    print(f"  • Platforms: {', '.join(loader.loaded_platforms) or 'None'}")
    print(f"  • Notification: {settings.notification_platform}")
    print(f"  • Review Lang: {settings.repo_review_lang}")
    print(f"  • LLM Model: {settings.ai_model}")
    print("="*60 + "\n")

    yield

    # Shutdown logic (if any)
    print("\n🛑 Seele Review Shutting down...")


app = FastAPI(
    title="SEELE Review FastAPI",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "SEELE Review API is running"}
