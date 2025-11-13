# from llama_index.core.bridge.langchain import ChatMessageHistory
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    """Enum for document processing status"""
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

class WebResource(BaseModel):
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    web_url: str
    isSummary: Optional[bool] = True
    page_content: Optional[str] = None 


class QueryResource(BaseModel):
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    web_url: str
    query: str
    ChatMessageHistory: dict

class Document(BaseModel):
    """Document model representing a web URL"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="User ID who owns the document")
    url: str = Field(..., description="Web URL of the document")
    dom: Optional[str] = Field(None, description="DOM content if available")
    title: Optional[str] = Field(None, description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    summary: Optional[str] = Field(None, description="AI-generated summary of the document content")
    processing_status: ProcessingStatus = Field(ProcessingStatus.QUEUED, description="Processing status of the document")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentCreate(BaseModel):
    """Model for creating a new document"""
    user_id: str
    url: str
    dom: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class Category(BaseModel):
    """Category model for organizing documents"""
    model_config = ConfigDict(
        populate_by_name=True
    )
    
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="User ID who owns the category")
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    document_ids: List[str] = Field(default_factory=list, description="List of document IDs in this category")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CategoryCreate(BaseModel):
    """Model for creating a new category"""
    user_id: str
    name: str
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    """Model for updating a category"""
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryDocumentOperation(BaseModel):
    """Model for adding/moving documents to a category"""
    document_ids: List[str] = Field(..., description="List of document IDs to add to category")


class CategorySummary(BaseModel):
    """Model for category summary with document subset"""
    category: Category
    category_news: Optional[str] = Field(None, description="Category news/updates, defaults to category description")
    representative_documents: List[Document] = Field(..., description="Representative/interesting documents from the category (recent by default)")
    total_documents: int = Field(..., description="Total number of documents in the category")
