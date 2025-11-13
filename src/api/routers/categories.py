"""
Category management API endpoints.
Handles category CRUD operations and document associations.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from bson import ObjectId
from bson.errors import InvalidId

from src.model.resource import (
    Category,
    CategoryCreate,
    CategoryUpdate,
    CategoryDocumentOperation,
    CategorySummary,
    Document
)
from src.service.category_service import CategoryService


router = APIRouter(prefix="/categories", tags=["categories"])
category_service = CategoryService()


@router.post("", response_model=Category, status_code=201)
async def create_category(category: CategoryCreate):
    """
    Create a new category for a user.
    
    Args:
        category: Category creation data
        
    Returns:
        Created category
        
    Raises:
        HTTPException: 409 if category already exists, 400 for other errors
    """
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


@router.get("", response_model=List[Category])
async def get_all_categories(
    user_id: str = Query(..., description="User ID to filter categories"),
    skip: int = Query(0, ge=0, description="Number of categories to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of categories to return")
) -> List[Category]:
    """
    Retrieve all categories for a specific user with pagination.
    
    Args:
        user_id: User ID to filter categories
        skip: Number of categories to skip (for pagination)
        limit: Maximum number of categories to return
        
    Returns:
        List of categories
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        categories = category_service.get_all_categories(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return categories
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{category_id}", response_model=Category)
async def get_category(
    category_id: str,
    user_id: str = Query(..., description="User ID")
) -> Category:
    """
    Retrieve a specific category by ID with ownership verification.
    
    Args:
        category_id: Category ID
        user_id: User ID for ownership verification
        
    Returns:
        Category details
        
    Raises:
        HTTPException: 404 if not found, 403 if not authorized
    """
    try:
        category = category_service.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Verify ownership
        if category.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this category"
            )
        
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{category_id}", response_model=Category)
async def update_category(
    category_id: str,
    update: CategoryUpdate,
    user_id: str = Query(..., description="User ID")
):
    """
    Update a category (rename or change description).
    
    Args:
        category_id: Category ID
        update: Category update data
        user_id: User ID for ownership verification
        
    Returns:
        Updated category
        
    Raises:
        HTTPException: 404 if not found, 409 if name conflict
    """
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


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    user_id: str = Query(..., description="User ID")
):
    """
    Delete a category.
    
    Args:
        category_id: Category ID
        user_id: User ID for ownership verification
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 400 if invalid ID format, 404 if not found
    """
    try:
        # Validate ObjectId format
        try:
            ObjectId(category_id)
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid category ID format"
            )
        
        deleted = category_service.delete_category(category_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return {"message": "Category deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{category_id}/documents", response_model=Category)
async def add_documents_to_category(
    category_id: str,
    operation: CategoryDocumentOperation,
    user_id: str = Query(..., description="User ID")
):
    """
    Add documents to a category.
    
    Args:
        category_id: Category ID
        operation: Document IDs to add
        user_id: User ID for ownership verification
        
    Returns:
        Updated category
        
    Raises:
        HTTPException: 404 if not found, 400 for invalid documents
    """
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


@router.delete("/{category_id}/documents", response_model=Category)
async def remove_documents_from_category(
    category_id: str,
    operation: CategoryDocumentOperation,
    user_id: str = Query(..., description="User ID")
):
    """
    Remove documents from a category.
    
    Args:
        category_id: Category ID
        operation: Document IDs to remove
        user_id: User ID for ownership verification
        
    Returns:
        Updated category
        
    Raises:
        HTTPException: 404 if not found
    """
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


@router.get("/{category_id}/documents", response_model=List[Document])
async def get_category_documents(
    category_id: str,
    user_id: str = Query(..., description="User ID"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents to return")
) -> List[Document]:
    """
    Retrieve all documents in a category.
    
    Args:
        category_id: Category ID
        user_id: User ID for ownership verification
        skip: Number of documents to skip (for pagination)
        limit: Maximum number of documents to return
        
    Returns:
        List of documents in the category
        
    Raises:
        HTTPException: If retrieval fails
    """
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


@router.get("/{category_id}/summary", response_model=CategorySummary)
async def get_category_summary(
    category_id: str,
    user_id: str = Query(..., description="User ID"),
    doc_limit: int = Query(
        3,
        ge=1,
        le=50,
        description="Number of representative documents to include in summary"
    ),
    category_news: Optional[str] = Query(
        None,
        description="Override for category news (defaults to category description)"
    )
) -> CategorySummary:
    """
    Get category summary with representative documents and category news.
    
    Args:
        category_id: Category ID
        user_id: User ID for ownership verification
        doc_limit: Number of representative documents to include
        category_news: Optional override for category news
        
    Returns:
        Category summary with documents
        
    Raises:
        HTTPException: 404 if not found
    """
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

