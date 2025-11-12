"""
Integration tests for Document REST API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.api.route import app


class TestDocumentAPI:
    """Test cases for Document API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, clean_documents_collection):
        """Setup for each test"""
        self.client = TestClient(app)
    
    def test_create_document(self):
        """Test POST /documents"""
        response = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "Test Document"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["user_id"] == "test_user"
        assert data["url"] == "https://example.com"
        assert data["title"] == "Test Document"
        assert "_id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_document_with_all_fields(self):
        """Test creating document with all optional fields"""
        response = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "Test Document",
                "description": "Test description",
                "dom": "<html><body>Test</body></html>"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test description"
        assert data["dom"] == "<html><body>Test</body></html>"
    
    def test_create_document_missing_required_fields(self):
        """Test creating document without required fields"""
        response = self.client.post(
            "/documents",
            json={
                "user_id": "test_user"
                # Missing url
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_all_documents_by_user(self):
        """Test GET /documents with user_id filter"""
        # Create some documents
        for i in range(3):
            self.client.post(
                "/documents",
                json={
                    "user_id": "user1",
                    "url": f"https://example.com/{i}",
                    "title": f"Document {i}"
                }
            )
        
        # Get documents for user1
        response = self.client.get("/documents?user_id=user1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all(doc["user_id"] == "user1" for doc in data)
    
    def test_get_all_documents_pagination(self):
        """Test pagination with skip and limit"""
        # Create 10 documents
        for i in range(10):
            self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": f"https://example.com/{i}",
                    "title": f"Document {i}"
                }
            )
        
        # Get first page
        response1 = self.client.get("/documents?user_id=test_user&skip=0&limit=5")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 5
        
        # Get second page
        response2 = self.client.get("/documents?user_id=test_user&skip=5&limit=5")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) == 5
        
        # Ensure no overlap
        ids1 = {doc["_id"] for doc in data1}
        ids2 = {doc["_id"] for doc in data2}
        assert len(ids1.intersection(ids2)) == 0
    
    def test_get_all_documents_missing_user_id(self):
        """Test GET /documents without required user_id"""
        response = self.client.get("/documents")
        
        # Should fail validation as user_id is required
        assert response.status_code == 422
    
    def test_get_document_by_id(self):
        """Test GET /documents/{document_id}"""
        # Create a document
        create_response = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "Test Document"
            }
        )
        doc_id = create_response.json()["_id"]
        
        # Get the document
        response = self.client.get(f"/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["_id"] == doc_id
        assert data["user_id"] == "test_user"
        assert data["url"] == "https://example.com"
    
    def test_get_document_by_id_not_found(self):
        """Test getting a non-existent document"""
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        response = self.client.get(f"/documents/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_document_by_id_invalid_id(self):
        """Test getting document with invalid ID format"""
        response = self.client.get("/documents/invalid_id")
        
        assert response.status_code == 400
    
    def test_delete_document(self):
        """Test DELETE /documents/{document_id}"""
        # Create a document
        create_response = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "Test Document"
            }
        )
        doc_id = create_response.json()["_id"]
        
        # Delete the document
        response = self.client.delete(f"/documents/{doc_id}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()
        
        # Verify it's gone
        get_response = self.client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 404
    
    def test_delete_document_not_found(self):
        """Test deleting a non-existent document"""
        fake_id = "507f1f77bcf86cd799439011"
        response = self.client.delete(f"/documents/{fake_id}")
        
        assert response.status_code == 404
    
    def test_create_duplicate_url_same_user(self):
        """Test that same user creating duplicate URL returns existing document (idempotent)"""
        # Create first document
        response1 = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "First"
            }
        )
        assert response1.status_code == 201
        first_doc = response1.json()
        
        # Try to create duplicate - should return existing document
        response2 = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "Second"  # Different title, but same URL
            }
        )
        
        # Should return 200 (not 201) and the same document
        assert response2.status_code == 200
        second_doc = response2.json()
        
        # Should be the same document ID (idempotent)
        assert second_doc["_id"] == first_doc["_id"]
        # Title should be from the first document (not updated)
        assert second_doc["title"] == "First"
    
    def test_create_same_url_different_users(self):
        """Test that different users can have the same URL"""
        # User 1 creates document
        response1 = self.client.post(
            "/documents",
            json={
                "user_id": "user1",
                "url": "https://example.com",
                "title": "User1 Doc"
            }
        )
        assert response1.status_code == 201
        
        # User 2 creates document with same URL
        response2 = self.client.post(
            "/documents",
            json={
                "user_id": "user2",
                "url": "https://example.com",
                "title": "User2 Doc"
            }
        )
        assert response2.status_code == 201
        
        # Both should have different IDs
        assert response1.json()["_id"] != response2.json()["_id"]
    
    def test_document_timestamps(self):
        """Test that created_at and updated_at are set correctly"""
        response = self.client.post(
            "/documents",
            json={
                "user_id": "test_user",
                "url": "https://example.com",
                "title": "Test"
            }
        )
        
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
    
    def test_full_document_lifecycle(self):
        """Test complete CRUD lifecycle"""
        # 1. Create
        create_response = self.client.post(
            "/documents",
            json={
                "user_id": "lifecycle_user",
                "url": "https://lifecycle.example.com",
                "title": "Lifecycle Test"
            }
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["_id"]
        
        # 2. Read (specific)
        get_response = self.client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Lifecycle Test"
        
        # 3. Read (list)
        list_response = self.client.get("/documents?user_id=lifecycle_user")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        
        # 4. Delete
        delete_response = self.client.delete(f"/documents/{doc_id}")
        assert delete_response.status_code == 200
        
        # 5. Verify deletion
        final_get = self.client.get(f"/documents/{doc_id}")
        assert final_get.status_code == 404
    
    def test_empty_user_documents(self):
        """Test getting documents for user with no documents"""
        response = self.client.get("/documents?user_id=nonexistent_user")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

