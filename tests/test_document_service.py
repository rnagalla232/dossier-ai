"""
Unit tests for DocumentService
"""
import pytest
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database

from src.service.document_service import DocumentService
from src.model.resource import DocumentCreate, Document


class TestDocumentService:
    """Test cases for DocumentService"""
    
    @pytest.fixture(autouse=True)
    def setup(self, clean_documents_collection):
        """Setup for each test"""
        self.service = DocumentService()
    
    def test_create_document(self):
        """Test creating a document"""
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        
        result, was_created = self.service.create_document(doc_create)
        
        assert isinstance(result, Document)
        assert was_created is True
        assert result.user_id == "test_user"
        assert result.url == "https://example.com"
        assert result.title == "Test Document"
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None
    
    def test_create_document_with_all_fields(self):
        """Test creating a document with all optional fields"""
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document",
            description="Test description",
            dom="<html><body>Test</body></html>"
        )
        
        result, was_created = self.service.create_document(doc_create)
        
        assert was_created is True
        assert result.description == "Test description"
        assert result.dom == "<html><body>Test</body></html>"
    
    def test_get_document_by_id(self):
        """Test retrieving a document by ID"""
        # Create a document first
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created, _ = self.service.create_document(doc_create)
        
        # Retrieve it
        result = self.service.get_document_by_id(created.id)
        
        assert result is not None
        assert isinstance(result, Document)
        assert result.id == created.id
        assert result.user_id == "test_user"
        assert result.url == "https://example.com"
    
    def test_get_document_by_id_not_found(self):
        """Test retrieving a non-existent document"""
        fake_id = str(ObjectId())
        result = self.service.get_document_by_id(fake_id)
        
        assert result is None
    
    def test_get_all_documents_by_user(self):
        """Test retrieving all documents for a user"""
        # Create multiple documents for different users
        for i in range(3):
            self.service.create_document(DocumentCreate(
                user_id="user1",
                url=f"https://example.com/{i}",
                title=f"Document {i}"
            ))
        
        for i in range(2):
            self.service.create_document(DocumentCreate(
                user_id="user2",
                url=f"https://example.com/user2/{i}",
                title=f"User2 Document {i}"
            ))
        
        # Get documents for user1
        user1_docs = self.service.get_all_documents(user_id="user1")
        assert len(user1_docs) == 3
        assert all(isinstance(doc, Document) for doc in user1_docs)
        assert all(doc.user_id == "user1" for doc in user1_docs)
        
        # Get documents for user2
        user2_docs = self.service.get_all_documents(user_id="user2")
        assert len(user2_docs) == 2
        assert all(doc.user_id == "user2" for doc in user2_docs)
    
    def test_get_all_documents_pagination(self):
        """Test pagination with skip and limit"""
        # Create 10 documents
        for i in range(10):
            self.service.create_document(DocumentCreate(
                user_id="test_user",
                url=f"https://example.com/{i}",
                title=f"Document {i}"
            ))
        
        # Get first page (5 documents)
        page1 = self.service.get_all_documents(user_id="test_user", skip=0, limit=5)
        assert len(page1) == 5
        
        # Get second page (5 documents)
        page2 = self.service.get_all_documents(user_id="test_user", skip=5, limit=5)
        assert len(page2) == 5
        
        # Ensure no overlap
        page1_ids = {doc.id for doc in page1}
        page2_ids = {doc.id for doc in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
    
    def test_get_all_documents_sorted_by_created_at(self):
        """Test that documents are sorted by created_at descending"""
        # Create documents with small delays to ensure different timestamps
        import time
        docs_created = []
        for i in range(3):
            doc, _ = self.service.create_document(DocumentCreate(
                user_id="test_user",
                url=f"https://example.com/{i}",
                title=f"Document {i}"
            ))
            docs_created.append(doc)
            time.sleep(0.01)  # Small delay
        
        # Get all documents
        retrieved = self.service.get_all_documents(user_id="test_user")
        
        # Should be in reverse order (most recent first)
        assert retrieved[0].id == docs_created[-1].id
        assert retrieved[-1].id == docs_created[0].id
    
    def test_delete_document(self):
        """Test deleting a document"""
        # Create a document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created, _ = self.service.create_document(doc_create)
        
        # Delete it
        result = self.service.delete_document(created.id)
        assert result is True
        
        # Verify it's gone
        retrieved = self.service.get_document_by_id(created.id)
        assert retrieved is None
    
    def test_delete_document_not_found(self):
        """Test deleting a non-existent document"""
        fake_id = str(ObjectId())
        result = self.service.delete_document(fake_id)
        assert result is False
    
    def test_get_document_count(self):
        """Test counting documents"""
        # Create documents for different users
        for i in range(3):
            self.service.create_document(DocumentCreate(
                user_id="user1",
                url=f"https://example.com/{i}",
                title=f"Document {i}"
            ))
        
        for i in range(2):
            self.service.create_document(DocumentCreate(
                user_id="user2",
                url=f"https://example.com/user2/{i}",
                title=f"User2 Document {i}"
            ))
        
        # Test counts
        assert self.service.get_document_count(user_id="user1") == 3
        assert self.service.get_document_count(user_id="user2") == 2
    
    def test_unique_constraint_user_url(self):
        """Test that API is idempotent - creating same document twice returns existing document"""
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        
        # Create first document
        doc1, was_created1 = self.service.create_document(doc_create)
        assert was_created1 is True
        
        # Try to create duplicate - should return existing document
        doc2, was_created2 = self.service.create_document(doc_create)
        assert was_created2 is False
        assert doc1.id == doc2.id
        assert doc1.user_id == doc2.user_id
        assert doc1.url == doc2.url
    
    def test_different_users_same_url(self):
        """Test that different users can have the same URL"""
        # User 1 creates a document
        doc1 = DocumentCreate(
            user_id="user1",
            url="https://example.com",
            title="User1 Document"
        )
        created1, was_created1 = self.service.create_document(doc1)
        
        # User 2 creates a document with same URL
        doc2 = DocumentCreate(
            user_id="user2",
            url="https://example.com",
            title="User2 Document"
        )
        created2, was_created2 = self.service.create_document(doc2)
        
        # Both should succeed and be created
        assert was_created1 is True
        assert was_created2 is True
        assert created1.id != created2.id
        assert created1.user_id == "user1"
        assert created2.user_id == "user2"

