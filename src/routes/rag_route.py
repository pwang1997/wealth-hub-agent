import asyncio
import os
from functools import lru_cache

import chromadb
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.params import Form
from llama_cloud_services import LlamaParse
from llama_index.core.embeddings import resolve_embed_model
from llama_index.core.node_parser import SentenceSplitter
from openai import OpenAI

router = APIRouter(prefix="/rag", tags=["investments"])


@lru_cache(maxsize=1)
def _get_chromadb_client():
    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    database = os.getenv("CHROMA_DATABASE")
    if api_key and tenant and database:
        return chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)

    host = os.getenv("CHROMA_HOST") or "localhost"
    port = int(os.getenv("CHROMA_PORT") or "8000")
    return chromadb.HttpClient(host=host, port=port)


@router.post("/upload_pdf")
async def upload_pdf(
    file: UploadFile,
    domain: str = "finance",
    corpus: str = "analyst_report",
    company_name: str | None = Form(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLAMA_CLOUD_API_KEY is not set.")

    parser = LlamaParse(
        api_key=api_key,  # can also be set in your env as LLAMA_CLOUD_API_KEY
        num_workers=4,  # if multiple files passed, split in `num_workers` API calls
        verbose=True,
        language="en",  # optionally define a language, default=en
    )

    file_bytes = await file.read()
    result = await parser.aparse(file_bytes, extra_info={"file_name": file.filename})

    markdown_documents = result.get_markdown_documents(split_by_page=True)

    try:
        embed_model = resolve_embed_model(os.getenv("RAG_EMBED_MODEL") or "default")
        splitter = SentenceSplitter(chunk_size=256)
        nodes = splitter.get_nodes_from_documents(markdown_documents)

        collection_name = f"{domain}_{corpus}_{company_name}"
        client = _get_chromadb_client()
        collection = client.get_or_create_collection(name=collection_name)

        ids = [node.id_ for node in nodes]
        documents = [node.get_content(metadata_mode="none") for node in nodes]
        metadatas = []
        for node in nodes:
            safe_metadata = {}
            for key, value in (node.metadata or {}).items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    safe_metadata[key] = value
                else:
                    safe_metadata[key] = str(value)
            safe_metadata.update(
                {
                    "source_file": file.filename,
                    "domain": domain,
                    "corpus": corpus,
                    "company_name": company_name,
                }
            )
            metadatas.append(safe_metadata)

        embeddings = await asyncio.to_thread(embed_model.get_text_embedding_batch, documents)
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index into ChromaDB: {e}") from e

    return {
        "collection_name": collection_name,
        "num_chunks_indexed": len(ids),
        "markdown_documents": markdown_documents,
    }


@router.get("/chat")
async def chat(
    query: str,
    domain: str = "finance",
    corpus: str = "analyst_report",
    company_name: str | None = "",
    top_k: int = 3,
):
    embed_model = resolve_embed_model(os.getenv("RAG_EMBED_MODEL") or "default")
    query_embedding = await asyncio.to_thread(embed_model.get_query_embedding, query)

    collection_name = f"{domain}_{corpus}_{company_name}"
    client = _get_chromadb_client()
    collection = client.get_or_create_collection(name=collection_name)

    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")

    context = _build_rag_context(results)
    oai = OpenAI(api_key=openai_api_key)
    response = await asyncio.to_thread(
        oai.responses.create,
        model="gpt-5-mini-2025-08-07",
        instructions=(
            "Answer the user's question using the provided context. "
            "If the context is insufficient, say so and ask a clarifying question."
        ),
        input=f"Context:\n{context}\n\nUser question:\n{query}",
    )

    return {
        "collection_name": collection_name,
        "response": getattr(response, "output_text", None) or str(response),
        "results": results,
    }


def _build_rag_context(results: dict, max_chars: int = 8000) -> str:
    documents = (results or {}).get("documents") or []
    metadatas = (results or {}).get("metadatas") or []
    distances = (results or {}).get("distances") or []
    ids = (results or {}).get("ids") or []

    docs = documents[0] if documents else []
    metas = metadatas[0] if metadatas else []
    dists = distances[0] if distances else []
    doc_ids = ids[0] if ids else []

    parts = []
    total_chars = 0
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else None
        dist = dists[i] if i < len(dists) else None
        doc_id = doc_ids[i] if i < len(doc_ids) else None
        chunk = f"[{i + 1}] id={doc_id} distance={dist} meta={meta}\n{doc}"
        parts.append(chunk)
        total_chars += len(chunk)
        if total_chars >= max_chars:
            break

    context = "\n\n---\n\n".join(parts)
    return context[:max_chars]
