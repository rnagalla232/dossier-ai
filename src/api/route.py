from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from typing import Optional, List
from src.model.resource import (
    WebResource, DocumentCreate, Document, 
    CategoryCreate, CategoryUpdate, Category, CategoryDocumentOperation, CategorySummary
)
from src.service.inference_pipeline import InferencePipelineService
from src.service.ingestion_pipeline import IngestionPipelineService
from src.service.retrieval_pipeline import RetrievalPipelineService
from src.service.document_service import DocumentService
from src.service.category_service import CategoryService
from src.service.queue_manager import queue_manager
import os

os.environ["OPENAI_API_KEY"] = "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"
os.environ["SNOWFLAKE_API_KEY"] = "eyJraWQiOiIxOTE1NjU4NjUwOSIsImFsZyI6IkVTMjU2In0.eyJwIjoiNzQ4MzAzNDA6NzQ4MzAzNDAiLCJpc3MiOiJTRjozMDAxIiwiZXhwIjoxNzYzMTYxMjk1fQ.x-pDBMNPyif_GokNywuAeApY_DIzBo3VzASxBRRWoj9OsXpfLEXsSvtc4kYtOI3_jDPANTwPNBP8Y9KCBKi6Mw"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",  # In case you use Live Server
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

document_service = DocumentService()
category_service = CategoryService()
inference_service = InferencePipelineService()


@app.get("/")
async def root():
    return {"message": "Server is running"}


@app.post("/documents", response_model=Document)
async def create_document(document: DocumentCreate):
    try:
        # Create document with QUEUED status (idempotent)
        doc, was_created = document_service.create_document(document)
        
        # Only enqueue for background processing if newly created
        if was_created:
            queue_manager.enqueue(
                document_id=doc.id,
                user_id=doc.user_id,
                metadata={
                    "url": doc.url,
                    "title": doc.title
                }
            )
        
        # Return appropriate status code: 201 for created, 200 for existing
        status_code = 201 if was_created else 200
        return JSONResponse(
            content=doc.model_dump(by_alias=True, mode='json'),
            status_code=status_code
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/documents", response_model=List[Document])
async def get_all_documents(
    user_id: str = Query(..., description="User ID to filter documents"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
) -> List[Document]:
    try:
        documents = document_service.get_all_documents(user_id=user_id, skip=skip, limit=limit)
        return documents
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/documents/{document_id}", response_model=Document)
async def get_document(document_id: str) -> Document:
    try:
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        deleted = document_service.delete_document(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "message": "Document deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/summary")
async def get_summary(resource: WebResource):
    return await inference_service.get_summary(resource=resource)

@app.post("/summary/stream")
async def chat_endpoint(resource: WebResource):
    return StreamingResponse(inference_service.get_summary(resource=resource), media_type="text/event-stream")

@app.post("/index/webresource")
async def index_file(resource: WebResource):
    return IngestionPipelineService().ingest_resource(resource=resource, split_type="recursive")


@app.post("/retrieve/query")
async def retrieve_file(resource: WebResource):
    return RetrievalPipelineService().query_vector_store(query=resource.query, top_k=2)


# Category Management Endpoints

@app.post("/categories", response_model=Category, status_code=201)
async def create_category(category: CategoryCreate):
    """Create a new category"""
    try:
        cat = category_service.create_category(category)
        return JSONResponse(
            content=cat.model_dump(by_alias=True, mode='json'),
            status_code=201
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/categories", response_model=List[Category])
async def get_all_categories(
    user_id: str = Query(..., description="User ID to filter categories"),
    skip: int = Query(0, ge=0, description="Number of categories to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of categories to return")
) -> List[Category]:
    """Get all categories for a user"""
    try:
        categories = category_service.get_all_categories(user_id=user_id, skip=skip, limit=limit)
        return categories
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: str, user_id: str = Query(..., description="User ID")) -> Category:
    """Get a category by ID"""
    try:
        category = category_service.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Verify ownership
        if category.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this category")
        
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/categories/{category_id}", response_model=Category)
async def update_category(
    category_id: str, 
    update: CategoryUpdate,
    user_id: str = Query(..., description="User ID")
):
    """Update a category (rename or change description)"""
    try:
        category = category_service.update_category(category_id, update, user_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return category
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Delete a category"""
    try:
        # Validate ObjectId format
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            ObjectId(category_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid category ID format")
        
        deleted = category_service.delete_category(category_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"message": "Category deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/categories/{category_id}/documents", response_model=Category)
async def add_documents_to_category(
    category_id: str,
    operation: CategoryDocumentOperation,
    user_id: str = Query(..., description="User ID")
):
    """Add documents to a category"""
    try:
        category = category_service.add_documents_to_category(
            category_id, 
            operation.document_ids, 
            user_id
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/categories/{category_id}/documents", response_model=Category)
async def remove_documents_from_category(
    category_id: str,
    operation: CategoryDocumentOperation,
    user_id: str = Query(..., description="User ID")
):
    """Remove documents from a category"""
    try:
        category = category_service.remove_documents_from_category(
            category_id, 
            operation.document_ids, 
            user_id
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/categories/{category_id}/documents", response_model=List[Document])
async def get_category_documents(
    category_id: str,
    user_id: str = Query(..., description="User ID"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
) -> List[Document]:
    """Get all documents in a category"""
    try:
        documents = category_service.get_documents_in_category(
            category_id=category_id,
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return documents
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/categories/{category_id}/summary", response_model=CategorySummary)
async def get_category_summary(
    category_id: str,
    user_id: str = Query(..., description="User ID"),
    doc_limit: int = Query(3, ge=1, le=50, description="Number of representative documents to include in summary"),
    category_news: Optional[str] = Query(None, description="Override for category news (defaults to category description)")
) -> CategorySummary:
    """Get category summary with representative documents and category news"""
    try:
        summary = category_service.get_category_summary(
            category_id=category_id,
            user_id=user_id,
            doc_limit=doc_limit,
            category_news=category_news
        )
        if not summary:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
