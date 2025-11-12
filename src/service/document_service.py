from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from src.helper.mongodb import mongodb_helper
from src.model.resource import Document, DocumentCreate, ProcessingStatus
from pymongo.collection import Collection


class DocumentService:
    """Service class for document operations"""
    
    def __init__(self):
        self.collection: Collection = mongodb_helper.get_collection("documents")
    
    def _mongo_doc_to_model(self, doc: Dict[str, Any]) -> Document:
        """Convert MongoDB document to Document model"""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return Document(**doc)
    
    def get_document_by_user_and_url(self, user_id: str, url: str) -> Optional[Document]:
        """Get a document by user_id and url"""
        try:
            doc = self.collection.find_one({"user_id": user_id, "url": url})
            if doc:
                return self._mongo_doc_to_model(doc)
            return None
        except Exception as e:
            raise Exception(f"Error retrieving document by user and url: {str(e)}")
    
    def create_document(self, document: DocumentCreate) -> tuple[Document, bool]:
        """
        Create a new document or return existing one (idempotent)
        Returns tuple of (document, was_created)
        """
        try:
            # Check if document already exists
            existing = self.get_document_by_user_and_url(document.user_id, document.url)
            if existing:
                return existing, False
            
            # Create new document
            doc_dict = document.model_dump()
            now = datetime.now(timezone.utc)
            doc_dict["created_at"] = now
            doc_dict["updated_at"] = now
            doc_dict["processing_status"] = ProcessingStatus.QUEUED.value
            
            result = self.collection.insert_one(doc_dict)
            
            # Retrieve the created document
            created_doc = self.collection.find_one({"_id": result.inserted_id})
            return self._mongo_doc_to_model(created_doc), True
        except Exception as e:
            raise Exception(f"Error creating document: {str(e)}")
    
    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        try:
            doc = self.collection.find_one({"_id": ObjectId(document_id)})
            if doc:
                return self._mongo_doc_to_model(doc)
            return None
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")
    
    def get_all_documents(
        self, 
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get all documents, optionally filtered by user_id"""
        try:
            query = {}
            if user_id:
                query["user_id"] = user_id
            
            cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
            documents = [self._mongo_doc_to_model(doc) for doc in cursor]
            return documents
        except Exception as e:
            raise Exception(f"Error retrieving documents: {str(e)}")

    def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        try:
            result = self.collection.delete_one({"_id": ObjectId(document_id)})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}")
    
    def get_document_count(self, user_id: Optional[str] = None) -> int:
        """Get total document count, optionally filtered by user_id"""
        try:
            query = {}
            if user_id:
                query["user_id"] = user_id
            return self.collection.count_documents(query)
        except Exception as e:
            raise Exception(f"Error counting documents: {str(e)}")
    
    def update_processing_status(self, document_id: str, status: ProcessingStatus) -> bool:
        """Update the processing status of a document"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "processing_status": status.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error updating processing status: {str(e)}")
    
    def update_document_summary(self, document_id: str, summary: str) -> bool:
        """Update the summary of a document"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "summary": summary,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error updating document summary: {str(e)}")

