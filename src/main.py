import logging

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

from src.routes.rag_route import router as rag_router

app = FastAPI(title="Wealth Hub Agent API", logger=logging.getLogger(__name__))

app.include_router(rag_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
