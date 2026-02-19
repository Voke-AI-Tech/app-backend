import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from config.settings import Settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Voke AI Speech Evaluation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _check_config():
    settings = Settings()
    missing = settings.missing_critical()
    if missing:
        logger.warning("Missing critical env vars: %s — AI features will be disabled", missing)
    else:
        logger.info("All critical env vars loaded (GOOGLE_API_KEY is set)")

@app.get("/")
def root():
    return {"status": "ok", "message": "Voke AI backend is running"}
@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
