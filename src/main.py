import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

from clients.chroma_client import ChromaClient
from src.routes.rag_route import router as rag_router
from src.routes.workflow_route import router as workflow_router

chroma_client = ChromaClient()


async def _check_chromadb() -> bool:
    try:
        client = chroma_client.get_client()
        await asyncio.to_thread(client.heartbeat)
        return True
    except Exception as exc:
        logger.warning("ChromaDB heartbeat failed", exc_info=exc)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    retries = int(os.getenv("CHROMA_STARTUP_RETRIES", "5"))
    delay_seconds = float(os.getenv("CHROMA_STARTUP_DELAY_SECONDS", "1.0"))
    for attempt in range(1, retries + 1):
        if await _check_chromadb():
            logger.info("ChromaDB heartbeat OK")
            break
        logger.warning("ChromaDB not ready (attempt %s/%s)", attempt, retries)
        await asyncio.sleep(delay_seconds)
    else:
        raise RuntimeError("ChromaDB did not become ready during startup")

    yield


app = FastAPI(
    title="Wealth Hub Agent API",
    logger=logger,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_router)
app.include_router(workflow_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
