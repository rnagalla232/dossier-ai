"""
Integration tests for Category API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.api.route import app
from src.service.category_service import CategoryService
from src.service.document_service import DocumentService
from src.model.resource import DocumentCreate
from pymongo.database import Database


class TestCategoryAPI:
    """Test suite for Category API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, test_db: Database):
        """Setup for each test"""
        test_db.categories.delete_many({})
        test_db.documents.delete_many({})
        self.client = TestClient(app)
        self.category_service = CategoryService()
        self.document_service = DocumentService()
        self.test_user_id = "test_user_123"
        yield
        test_db.categories.delete_many({})
        test_db.documents.delete_many({})

    def test_create_category_success(self):
        """Test POST /categories - successful creation"""
        response = self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "Technology",
                "description": "Tech articles"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == self.test_user_id
        assert data["name"] == "Technology"
        assert data["description"] == "Tech articles"
        assert data["document_ids"] == []
        assert "_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_category_without_description(self):
        """Test creating category without description"""
        response = self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "Business"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Business"
        assert data.get("description") is None

    def test_create_category_duplicate_name(self):
        """Test creating category with duplicate name returns 409"""
        # Create first category
        self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "Technology"
            }
        )
        
        # Try to create duplicate
        response = self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "Technology"
            }
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_category_missing_required_fields(self):
        """Test creating category without required fields"""
        response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id}
        )
        
        assert response.status_code == 422  # Validation error

    def test_get_all_categories_success(self):
        """Test GET /categories - get all categories for user"""
        # Create multiple categories
        for name in ["Tech", "Business", "Science"]:
            self.client.post(
                "/categories",
                json={"user_id": self.test_user_id, "name": name}
            )
        
        # Create category for different user
        self.client.post(
            "/categories",
            json={"user_id": "other_user", "name": "Other"}
        )
        
        response = self.client.get(f"/categories?user_id={self.test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        category_names = [cat["name"] for cat in data]
        assert "Tech" in category_names
        assert "Business" in category_names
        assert "Science" in category_names
        assert "Other" not in category_names

    def test_get_all_categories_pagination(self):
        """Test pagination for getting categories"""
        # Create 5 categories
        for i in range(5):
            self.client.post(
                "/categories",
                json={"user_id": self.test_user_id, "name": f"Category{i}"}
            )
        
        # Get first page
        response1 = self.client.get(
            f"/categories?user_id={self.test_user_id}&skip=0&limit=2"
        )
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1) == 2
        
        # Get second page
        response2 = self.client.get(
            f"/categories?user_id={self.test_user_id}&skip=2&limit=2"
        )
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2) == 2
        
        # Ensure pages don't overlap
        assert page1[0]["_id"] != page2[0]["_id"]

    def test_get_all_categories_empty(self):
        """Test getting categories when none exist"""
        response = self.client.get(f"/categories?user_id={self.test_user_id}")
        
        assert response.status_code == 200
        assert response.json() == []

    def test_get_category_by_id_success(self):
        """Test GET /categories/{category_id} - successful retrieval"""
        # Create category
        create_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Technology"}
        )
        category_id = create_response.json()["_id"]
        
        # Get category
        response = self.client.get(
            f"/categories/{category_id}?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["_id"] == category_id
        assert data["name"] == "Technology"

    def test_get_category_by_id_not_found(self):
        """Test getting non-existent category returns 404"""
        response = self.client.get(
            f"/categories/507f1f77bcf86cd799439011?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_category_by_id_wrong_user(self):
        """Test getting category with wrong user_id returns 403"""
        # Create category for user1
        create_response = self.client.post(
            "/categories",
            json={"user_id": "user1", "name": "Technology"}
        )
        category_id = create_response.json()["_id"]
        
        # Try to get with different user
        response = self.client.get(
            f"/categories/{category_id}?user_id=user2"
        )
        
        assert response.status_code == 403

    def test_update_category_name_success(self):
        """Test PATCH /categories/{category_id} - update name"""
        # Create category
        create_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Old Name"}
        )
        category_id = create_response.json()["_id"]
        
        # Update name
        response = self.client.patch(
            f"/categories/{category_id}?user_id={self.test_user_id}",
            json={"name": "New Name"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["_id"] == category_id

    def test_update_category_description(self):
        """Test updating category description"""
        create_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech"}
        )
        category_id = create_response.json()["_id"]
        
        response = self.client.patch(
            f"/categories/{category_id}?user_id={self.test_user_id}",
            json={"description": "New description"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"
        assert data["name"] == "Tech"  # Name unchanged

    def test_update_category_both_fields(self):
        """Test updating both name and description"""
        create_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Old"}
        )
        category_id = create_response.json()["_id"]
        
        response = self.client.patch(
            f"/categories/{category_id}?user_id={self.test_user_id}",
            json={"name": "New", "description": "New description"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New"
        assert data["description"] == "New description"

    def test_update_category_duplicate_name(self):
        """Test updating to duplicate name returns 409"""
        self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Category1"}
        )
        create_response2 = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Category2"}
        )
        category_id = create_response2.json()["_id"]
        
        response = self.client.patch(
            f"/categories/{category_id}?user_id={self.test_user_id}",
            json={"name": "Category1"}
        )
        
        assert response.status_code == 409

    def test_update_category_not_found(self):
        """Test updating non-existent category returns 404"""
        response = self.client.patch(
            f"/categories/507f1f77bcf86cd799439011?user_id={self.test_user_id}",
            json={"name": "New Name"}
        )
        
        assert response.status_code == 404

    def test_add_documents_to_category_success(self):
        """Test POST /categories/{category_id}/documents - add documents"""
        # Create category
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create documents
        doc1, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/1")
        )
        doc2, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/2")
        )
        
        # Add documents to category
        response = self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": [doc1.id, doc2.id]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["document_ids"]) == 2
        assert doc1.id in data["document_ids"]
        assert doc2.id in data["document_ids"]

    def test_add_documents_to_category_not_found(self):
        """Test adding documents to non-existent category"""
        response = self.client.post(
            f"/categories/507f1f77bcf86cd799439011/documents?user_id={self.test_user_id}",
            json={"document_ids": ["507f1f77bcf86cd799439012"]}
        )
        
        assert response.status_code == 404

    def test_add_nonexistent_documents_to_category(self):
        """Test adding non-existent documents returns 400"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech"}
        )
        category_id = cat_response.json()["_id"]
        
        response = self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": ["507f1f77bcf86cd799439011"]}
        )
        
        assert response.status_code == 400

    def test_remove_documents_from_category_success(self):
        """Test DELETE /categories/{category_id}/documents - remove documents"""
        # Create category
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create and add documents
        doc1, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/1")
        )
        doc2, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/2")
        )
        
        self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": [doc1.id, doc2.id]}
        )
        
        # Remove one document
        response = self.client.request(
            "DELETE",
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": [doc1.id]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["document_ids"]) == 1
        assert doc2.id in data["document_ids"]
        assert doc1.id not in data["document_ids"]

    def test_get_category_documents_success(self):
        """Test GET /categories/{category_id}/documents - get all documents"""
        # Create category
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create and add documents
        doc_ids = []
        for i in range(3):
            doc, _ = self.document_service.create_document(
                DocumentCreate(
                    user_id=self.test_user_id,
                    url=f"https://example.com/{i}",
                    title=f"Article {i}"
                )
            )
            doc_ids.append(doc.id)
        
        self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": doc_ids}
        )
        
        # Get documents
        response = self.client.get(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 200
        documents = response.json()
        assert len(documents) == 3
        retrieved_ids = [doc["_id"] for doc in documents]
        for doc_id in doc_ids:
            assert doc_id in retrieved_ids

    def test_get_category_documents_empty(self):
        """Test getting documents from empty category"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Empty"}
        )
        category_id = cat_response.json()["_id"]
        
        response = self.client.get(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 200
        assert response.json() == []

    def test_get_category_documents_pagination(self):
        """Test pagination for getting category documents"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create and add 5 documents
        doc_ids = []
        for i in range(5):
            doc, _ = self.document_service.create_document(
                DocumentCreate(user_id=self.test_user_id, url=f"https://example.com/{i}")
            )
            doc_ids.append(doc.id)
        
        self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": doc_ids}
        )
        
        # Get first page
        response1 = self.client.get(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}&skip=0&limit=2"
        )
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1) == 2
        
        # Get second page
        response2 = self.client.get(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}&skip=2&limit=2"
        )
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2) == 2

    def test_get_category_summary_success(self):
        """Test GET /categories/{category_id}/summary - get summary"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech", "description": "Technology articles"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create and add 10 documents
        doc_ids = []
        for i in range(10):
            doc, _ = self.document_service.create_document(
                DocumentCreate(
                    user_id=self.test_user_id,
                    url=f"https://example.com/{i}",
                    title=f"Article {i}"
                )
            )
            doc_ids.append(doc.id)
        
        self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": doc_ids}
        )
        
        # Get summary with limit of 3
        response = self.client.get(
            f"/categories/{category_id}/summary?user_id={self.test_user_id}&doc_limit=3"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"]["_id"] == category_id
        assert data["category"]["name"] == "Tech"
        assert data["category_news"] == "Technology articles"  # Defaults to description
        assert len(data["representative_documents"]) <= 3
        assert data["total_documents"] == 10

    def test_get_category_summary_default_limit(self):
        """Test getting summary with default document limit (3)"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech", "description": "Tech news"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create and add 8 documents
        doc_ids = []
        for i in range(8):
            doc, _ = self.document_service.create_document(
                DocumentCreate(user_id=self.test_user_id, url=f"https://example.com/{i}")
            )
            doc_ids.append(doc.id)
        
        self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": doc_ids}
        )
        
        # Get summary without doc_limit (should default to 3)
        response = self.client.get(
            f"/categories/{category_id}/summary?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["representative_documents"]) <= 3  # Default is now 3
        assert data["total_documents"] == 8
        assert data["category_news"] == "Tech news"  # Defaults to description

    def test_get_category_summary_empty_category(self):
        """Test getting summary for empty category"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Empty", "description": "Empty for now"}
        )
        category_id = cat_response.json()["_id"]
        
        response = self.client.get(
            f"/categories/{category_id}/summary?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"]["name"] == "Empty"
        assert data["category_news"] == "Empty for now"
        assert len(data["representative_documents"]) == 0
        assert data["total_documents"] == 0

    def test_get_category_summary_not_found(self):
        """Test getting summary for non-existent category"""
        response = self.client.get(
            f"/categories/507f1f77bcf86cd799439011/summary?user_id={self.test_user_id}"
        )
        
        assert response.status_code == 404
    
    def test_get_category_summary_with_custom_news(self):
        """Test getting summary with custom category news override"""
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech", "description": "Tech articles"}
        )
        category_id = cat_response.json()["_id"]
        
        # Create and add documents
        doc_ids = []
        for i in range(5):
            doc, _ = self.document_service.create_document(
                DocumentCreate(user_id=self.test_user_id, url=f"https://example.com/{i}")
            )
            doc_ids.append(doc.id)
        
        self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": doc_ids}
        )
        
        # Get summary with custom category_news
        custom_news = "Breaking: New AI models released!"
        response = self.client.get(
            f"/categories/{category_id}/summary?user_id={self.test_user_id}&category_news={custom_news}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category_news"] == custom_news  # Should use custom news
        assert data["category_news"] != "Tech articles"  # Not the default description

    def test_category_workflow_complete(self):
        """Test complete workflow: create, update, add docs, get summary"""
        # 1. Create category
        cat_response = self.client.post(
            "/categories",
            json={"user_id": self.test_user_id, "name": "Tech Articles"}
        )
        assert cat_response.status_code == 201
        category_id = cat_response.json()["_id"]
        
        # 2. Update category description
        update_response = self.client.patch(
            f"/categories/{category_id}?user_id={self.test_user_id}",
            json={"description": "Technology and innovation articles"}
        )
        assert update_response.status_code == 200
        
        # 3. Create and add documents
        doc_ids = []
        for i in range(5):
            doc, _ = self.document_service.create_document(
                DocumentCreate(
                    user_id=self.test_user_id,
                    url=f"https://example.com/tech/{i}",
                    title=f"Tech Article {i}"
                )
            )
            doc_ids.append(doc.id)
        
        add_response = self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": doc_ids}
        )
        assert add_response.status_code == 200
        
        # 4. Get category summary
        summary_response = self.client.get(
            f"/categories/{category_id}/summary?user_id={self.test_user_id}"
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["category"]["name"] == "Tech Articles"
        assert summary["category"]["description"] == "Technology and innovation articles"
        assert summary["total_documents"] == 5
        
        # 5. Get all documents in category
        docs_response = self.client.get(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}"
        )
        assert docs_response.status_code == 200
        assert len(docs_response.json()) == 5
        
        # 6. Remove a document
        remove_response = self.client.request(
            "DELETE",
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": [doc_ids[0]]}
        )
        assert remove_response.status_code == 200
        
        # 7. Verify document was removed
        final_summary = self.client.get(
            f"/categories/{category_id}/summary?user_id={self.test_user_id}"
        )
        assert final_summary.json()["total_documents"] == 4
    
    def test_delete_category_success(self):
        """Test successful category deletion"""
        # Create a category
        create_response = self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "ToDelete",
                "description": "This category will be deleted"
            }
        )
        assert create_response.status_code == 201
        category_id = create_response.json()["_id"]
        
        # Delete the category
        delete_response = self.client.delete(
            f"/categories/{category_id}?user_id={self.test_user_id}"
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Category deleted successfully"
        
        # Verify category is gone
        get_response = self.client.get(
            f"/categories/{category_id}?user_id={self.test_user_id}"
        )
        assert get_response.status_code == 404
    
    def test_delete_category_not_found(self):
        """Test deleting a non-existent category"""
        from bson import ObjectId
        fake_id = str(ObjectId())
        
        delete_response = self.client.delete(
            f"/categories/{fake_id}?user_id={self.test_user_id}"
        )
        assert delete_response.status_code == 404
        assert delete_response.json()["detail"] == "Category not found"
    
    def test_delete_category_wrong_user(self):
        """Test that user cannot delete another user's category"""
        # Create a category for one user
        create_response = self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "UserCategory",
                "description": "Belongs to test user"
            }
        )
        assert create_response.status_code == 201
        category_id = create_response.json()["_id"]
        
        # Try to delete it as a different user
        delete_response = self.client.delete(
            f"/categories/{category_id}?user_id=other_user"
        )
        assert delete_response.status_code == 404
        
        # Verify category still exists for original user
        get_response = self.client.get(
            f"/categories/{category_id}?user_id={self.test_user_id}"
        )
        assert get_response.status_code == 200
    
    def test_delete_category_with_documents(self):
        """Test deleting a category that has documents"""
        # Create a category
        create_cat_response = self.client.post(
            "/categories",
            json={
                "user_id": self.test_user_id,
                "name": "CategoryWithDocs",
                "description": "Has documents"
            }
        )
        assert create_cat_response.status_code == 201
        category_id = create_cat_response.json()["_id"]
        
        # Create and add documents
        doc1_response = self.client.post(
            "/documents",
            json={
                "user_id": self.test_user_id,
                "url": "https://example.com/doc1",
                "title": "Document 1"
            }
        )
        doc2_response = self.client.post(
            "/documents",
            json={
                "user_id": self.test_user_id,
                "url": "https://example.com/doc2",
                "title": "Document 2"
            }
        )
        doc1_id = doc1_response.json()["_id"]
        doc2_id = doc2_response.json()["_id"]
        
        # Add documents to category
        add_response = self.client.post(
            f"/categories/{category_id}/documents?user_id={self.test_user_id}",
            json={"document_ids": [doc1_id, doc2_id]}
        )
        assert add_response.status_code == 200
        
        # Delete the category
        delete_response = self.client.delete(
            f"/categories/{category_id}?user_id={self.test_user_id}"
        )
        assert delete_response.status_code == 200
        
        # Verify category is gone
        get_cat_response = self.client.get(
            f"/categories/{category_id}?user_id={self.test_user_id}"
        )
        assert get_cat_response.status_code == 404
        
        # Verify documents still exist
        doc1_get = self.client.get(f"/documents/{doc1_id}")
        doc2_get = self.client.get(f"/documents/{doc2_id}")
        assert doc1_get.status_code == 200
        assert doc2_get.status_code == 200
    
    def test_delete_category_missing_user_id(self):
        """Test deleting category without user_id"""
        from bson import ObjectId
        fake_id = str(ObjectId())
        
        delete_response = self.client.delete(f"/categories/{fake_id}")
        assert delete_response.status_code == 422  # Validation error

