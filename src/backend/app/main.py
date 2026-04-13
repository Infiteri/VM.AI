import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.logging_config import setup_logging
from app.utils.cleanup import run_cleanup_loop

# Initialize logging immediately
logger = setup_logging()

app = FastAPI(
    title="VM.AI Backend",
    description="AI-driven personal scheduling system for ONIA 2026",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """
    This event runs automatically when the server starts.
    It initializes the background garbage collector.
    """
    logger.info("VM.AI Backend Starting...")
    # Start the cleanup loop in the background
    asyncio.create_task(run_cleanup_loop())

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "VM.AI Backend is running"}

app.include_router(api_router, prefix="/api/v1")