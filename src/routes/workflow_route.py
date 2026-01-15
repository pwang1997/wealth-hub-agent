import logging
from http.client import INTERNAL_SERVER_ERROR

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.orchestrator.orchestrator import WorkflowOrchestrator
from src.orchestrator.types import StreamEvent, WorkflowRequest, WorkflowResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/workflow", tags=["workflow"])
orchestrator = WorkflowOrchestrator()


@router.post("/run", response_model=WorkflowResponse)
async def run_workflow(request: WorkflowRequest):
    """
    Execute a workflow synchronously.
    """
    try:
        return await orchestrator.run_workflow(request)
    except Exception as e:
        logger.exception("Workflow execution failed")
        raise HTTPException(status_code=INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post("/stream")
async def stream_workflow(request: WorkflowRequest):
    """
    Execute a workflow and stream events (SSE).
    """

    async def event_generator():
        workflow_id = request.workflow_id or "wf_" + str(
            request.query.__hash__()
        )  # temporary ID gen if missing
        assert workflow_id is not None
        # The orchestrator handles ID generation internally if passed None,
        # but for streaming we might want consistency if we rely on the ID outside.
        # Actually types.py says WorkflowRequest has optional workflow_id.
        # orchestrator.workflow_generator takes a strictly typed string workflow_id.
        # So we should generate it here if missing.
        import uuid

        effective_id = request.workflow_id or str(uuid.uuid4())

        try:
            async for event in orchestrator.workflow_generator(request, effective_id):
                # SSE format: data: <json>\n\n
                yield f"data: {event.model_dump_json()}\n\n"
        except Exception as e:
            logger.exception("Streaming workflow failed")
            # We try to emit an error event if the stream is still open
            error_event = StreamEvent(
                workflow_id=effective_id, event="error", status="failed", payload={"error": str(e)}
            )
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
