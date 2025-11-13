"""
Document management API endpoints.
Handles CRUD operations for documents and background processing.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.model.resource import Document, DocumentCreate
from src.service.document_service import DocumentService
from src.service.queue_manager import queue_manager


router = APIRouter(prefix="/documents", tags=["documents"])
document_service = DocumentService()


@router.post("", response_model=Document, status_code=201)
async def create_document(document: DocumentCreate):
    """
    Create a new document and enqueue it for background processing.
    
    Args:
        document: Document creation data
        
    Returns:
        Created document with status code 201 (new) or 200 (existing)
        
    Raises:
        HTTPException: If document creation fails
    """
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


@router.get("", response_model=List[Document])
async def get_all_documents(
    user_id: str = Query(..., description="User ID to filter documents"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
) -> List[Document]:
    """
    Retrieve all documents for a specific user with pagination.
    
    Args:
        user_id: User ID to filter documents
        skip: Number of documents to skip (for pagination)
        limit: Maximum number of documents to return
        
    Returns:
        List of documents
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        documents = document_service.get_all_documents(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return documents
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: str) -> Document:
    """
    Retrieve a specific document by ID.
    
    Args:
        document_id: Document ID
        
    Returns:
        Document details
        
    Raises:
        HTTPException: If document not found or retrieval fails
    """
    try:
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a specific document by ID.
    
    Args:
        document_id: Document ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        deleted = document_service.delete_document(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

