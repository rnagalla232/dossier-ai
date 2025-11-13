"""
Inference and processing API endpoints.
Handles summarization, streaming, indexing, and retrieval operations.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.model.resource import WebResource
from src.service.inference_pipeline import InferencePipelineService
from src.service.ingestion_pipeline import IngestionPipelineService
from src.service.retrieval_pipeline import RetrievalPipelineService


router = APIRouter(tags=["inference"])

inference_service = InferencePipelineService()
ingestion_service = IngestionPipelineService()
retrieval_service = RetrievalPipelineService()


@router.post("/summary")
async def get_summary(resource: WebResource):
    """
    Generate a summary of web content (non-streaming).
    
    Args:
        resource: Web resource containing content to summarize
        
    Returns:
        Summary result
    """
    return await inference_service.get_summary(resource=resource)


@router.post("/summary/stream")
async def stream_summary(resource: WebResource):
    """
    Generate a streaming summary of web content.
    
    Args:
        resource: Web resource containing content to summarize
        
    Returns:
        Server-sent events stream with summary chunks
    """
    return StreamingResponse(
        inference_service.get_summary(resource=resource),
        media_type="text/event-stream"
    )


@router.post("/index/webresource")
async def index_web_resource(resource: WebResource):
    """
    Index web resource content for retrieval.
    
    Args:
        resource: Web resource to index
        
    Returns:
        Indexing result
    """
    return ingestion_service.ingest_resource(
        resource=resource,
        split_type="recursive"
    )


@router.post("/retrieve/query")
async def retrieve_query(resource: WebResource):
    """
    Retrieve similar content based on a query.
    
    Args:
        resource: Resource containing query
        
    Returns:
        Retrieved results
    """
    return retrieval_service.query_vector_store(
        query=resource.query,
        top_k=2
    )

