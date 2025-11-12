"""
Unit tests for CategoryService
"""
import pytest
from src.service.category_service import CategoryService
from src.service.document_service import DocumentService
from src.model.resource import CategoryCreate, CategoryUpdate, DocumentCreate
from pymongo.database import Database


class TestCategoryService:
    """Test suite for CategoryService"""

    @pytest.fixture(autouse=True)
    def setup(self, test_db: Database):
        """Setup for each test"""
        # Clean up before and after each test
        test_db.categories.delete_many({})
        test_db.documents.delete_many({})
        self.category_service = CategoryService()
        self.document_service = DocumentService()
        self.test_user_id = "test_user_123"
        yield
        # Cleanup after test
        test_db.categories.delete_many({})
        test_db.documents.delete_many({})

    def test_create_category_success(self):
        """Test successful category creation"""
        category_create = CategoryCreate(
            user_id=self.test_user_id,
            name="Technology",
            description="Tech articles"
        )
        
        category = self.category_service.create_category(category_create)
        
        assert category is not None
        assert category.id is not None
        assert category.user_id == self.test_user_id
        assert category.name == "Technology"
        assert category.description == "Tech articles"
        assert category.document_ids == []
        assert category.created_at is not None
        assert category.updated_at is not None

    def test_create_category_without_description(self):
        """Test category creation without description"""
        category_create = CategoryCreate(
            user_id=self.test_user_id,
            name="Business"
        )
        
        category = self.category_service.create_category(category_create)
        
        assert category is not None
        assert category.name == "Business"
        assert category.description is None

    def test_create_duplicate_category_name_fails(self):
        """Test that creating a category with duplicate name fails"""
        category_create = CategoryCreate(
            user_id=self.test_user_id,
            name="Technology"
        )
        
        # Create first category
        self.category_service.create_category(category_create)
        
        # Try to create duplicate - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            self.category_service.create_category(category_create)
        
        assert "already exists" in str(exc_info.value)

    def test_create_same_category_name_different_users(self):
        """Test that different users can have categories with the same name"""
        category_create_user1 = CategoryCreate(
            user_id="user1",
            name="Technology"
        )
        category_create_user2 = CategoryCreate(
            user_id="user2",
            name="Technology"
        )
        
        cat1 = self.category_service.create_category(category_create_user1)
        cat2 = self.category_service.create_category(category_create_user2)
        
        assert cat1.user_id == "user1"
        assert cat2.user_id == "user2"
        assert cat1.name == cat2.name == "Technology"
        assert cat1.id != cat2.id

    def test_get_category_by_id_success(self):
        """Test getting a category by ID"""
        category_create = CategoryCreate(
            user_id=self.test_user_id,
            name="Science"
        )
        
        created = self.category_service.create_category(category_create)
        retrieved = self.category_service.get_category_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Science"

    def test_get_category_by_id_not_found(self):
        """Test getting a non-existent category"""
        result = self.category_service.get_category_by_id("507f1f77bcf86cd799439011")
        assert result is None

    def test_get_all_categories_for_user(self):
        """Test getting all categories for a user"""
        # Create multiple categories
        for name in ["Tech", "Business", "Science"]:
            self.category_service.create_category(
                CategoryCreate(user_id=self.test_user_id, name=name)
            )
        
        # Create category for different user
        self.category_service.create_category(
            CategoryCreate(user_id="other_user", name="Other")
        )
        
        categories = self.category_service.get_all_categories(self.test_user_id)
        
        assert len(categories) == 3
        category_names = [cat.name for cat in categories]
        assert "Tech" in category_names
        assert "Business" in category_names
        assert "Science" in category_names
        assert "Other" not in category_names

    def test_get_all_categories_pagination(self):
        """Test pagination for getting categories"""
        # Create 5 categories
        for i in range(5):
            self.category_service.create_category(
                CategoryCreate(user_id=self.test_user_id, name=f"Category{i}")
            )
        
        # Test skip and limit
        page1 = self.category_service.get_all_categories(self.test_user_id, skip=0, limit=2)
        page2 = self.category_service.get_all_categories(self.test_user_id, skip=2, limit=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_update_category_name(self):
        """Test updating category name"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Old Name")
        )
        
        update = CategoryUpdate(name="New Name")
        updated = self.category_service.update_category(category.id, update, self.test_user_id)
        
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.id == category.id

    def test_update_category_description(self):
        """Test updating category description"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        update = CategoryUpdate(description="Technology articles")
        updated = self.category_service.update_category(category.id, update, self.test_user_id)
        
        assert updated is not None
        assert updated.description == "Technology articles"
        assert updated.name == "Tech"  # Name should remain unchanged

    def test_update_category_both_fields(self):
        """Test updating both name and description"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Old", description="Old desc")
        )
        
        update = CategoryUpdate(name="New", description="New desc")
        updated = self.category_service.update_category(category.id, update, self.test_user_id)
        
        assert updated is not None
        assert updated.name == "New"
        assert updated.description == "New desc"

    def test_update_category_duplicate_name_fails(self):
        """Test that updating to a duplicate name fails"""
        cat1 = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Category1")
        )
        cat2 = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Category2")
        )
        
        # Try to rename cat2 to cat1's name
        update = CategoryUpdate(name="Category1")
        with pytest.raises(ValueError) as exc_info:
            self.category_service.update_category(cat2.id, update, self.test_user_id)
        
        assert "already exists" in str(exc_info.value)

    def test_update_category_wrong_user_returns_none(self):
        """Test that updating a category with wrong user_id returns None"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        update = CategoryUpdate(name="New Name")
        result = self.category_service.update_category(category.id, update, "wrong_user")
        
        assert result is None

    def test_add_documents_to_category(self):
        """Test adding documents to a category"""
        # Create category
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        # Create documents
        doc1, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/1")
        )
        doc2, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/2")
        )
        
        # Add documents to category
        updated = self.category_service.add_documents_to_category(
            category.id, [doc1.id, doc2.id], self.test_user_id
        )
        
        assert updated is not None
        assert len(updated.document_ids) == 2
        assert doc1.id in updated.document_ids
        assert doc2.id in updated.document_ids

    def test_add_documents_idempotent(self):
        """Test that adding the same document twice doesn't duplicate"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        doc, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/1")
        )
        
        # Add document twice
        self.category_service.add_documents_to_category(
            category.id, [doc.id], self.test_user_id
        )
        updated = self.category_service.add_documents_to_category(
            category.id, [doc.id], self.test_user_id
        )
        
        # Should only have one instance
        assert len(updated.document_ids) == 1

    def test_add_nonexistent_documents_fails(self):
        """Test that adding non-existent documents fails"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        fake_doc_id = "507f1f77bcf86cd799439011"
        
        with pytest.raises(ValueError) as exc_info:
            self.category_service.add_documents_to_category(
                category.id, [fake_doc_id], self.test_user_id
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_add_documents_wrong_user_fails(self):
        """Test that adding documents from different user fails"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        doc, _ = self.document_service.create_document(
            DocumentCreate(user_id="other_user", url="https://example.com/1")
        )
        
        with pytest.raises(ValueError):
            self.category_service.add_documents_to_category(
                category.id, [doc.id], self.test_user_id
            )

    def test_remove_documents_from_category(self):
        """Test removing documents from a category"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        # Create and add documents
        doc1, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/1")
        )
        doc2, _ = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/2")
        )
        
        self.category_service.add_documents_to_category(
            category.id, [doc1.id, doc2.id], self.test_user_id
        )
        
        # Remove one document
        updated = self.category_service.remove_documents_from_category(
            category.id, [doc1.id], self.test_user_id
        )
        
        assert len(updated.document_ids) == 1
        assert doc2.id in updated.document_ids
        assert doc1.id not in updated.document_ids

    def test_get_documents_in_category(self):
        """Test getting all documents in a category"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        # Create and add documents
        doc_ids = []
        for i in range(3):
            doc, _ = self.document_service.create_document(
                DocumentCreate(user_id=self.test_user_id, url=f"https://example.com/{i}")
            )
            doc_ids.append(doc.id)
        
        self.category_service.add_documents_to_category(
            category.id, doc_ids, self.test_user_id
        )
        
        # Get documents
        documents = self.category_service.get_documents_in_category(
            category.id, self.test_user_id
        )
        
        assert len(documents) == 3
        retrieved_ids = [doc.id for doc in documents]
        for doc_id in doc_ids:
            assert doc_id in retrieved_ids

    def test_get_documents_in_empty_category(self):
        """Test getting documents from an empty category"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Empty")
        )
        
        documents = self.category_service.get_documents_in_category(
            category.id, self.test_user_id
        )
        
        assert documents == []

    def test_get_documents_in_category_pagination(self):
        """Test pagination for getting documents in category"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech")
        )
        
        # Create and add 5 documents
        doc_ids = []
        for i in range(5):
            doc, _ = self.document_service.create_document(
                DocumentCreate(user_id=self.test_user_id, url=f"https://example.com/{i}")
            )
            doc_ids.append(doc.id)
        
        self.category_service.add_documents_to_category(
            category.id, doc_ids, self.test_user_id
        )
        
        # Test pagination
        page1 = self.category_service.get_documents_in_category(
            category.id, self.test_user_id, skip=0, limit=2
        )
        page2 = self.category_service.get_documents_in_category(
            category.id, self.test_user_id, skip=2, limit=2
        )
        
        assert len(page1) == 2
        assert len(page2) == 2

    def test_get_category_summary(self):
        """Test getting category summary with representative documents"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech", description="Technology articles")
        )
        
        # Create and add documents
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
        
        self.category_service.add_documents_to_category(
            category.id, doc_ids, self.test_user_id
        )
        
        # Get summary with default limit (3 documents)
        summary = self.category_service.get_category_summary(
            category.id, self.test_user_id
        )
        
        assert summary is not None
        assert summary.category.id == category.id
        assert summary.category.name == "Tech"
        assert summary.category_news == "Technology articles"  # Defaults to description
        assert len(summary.representative_documents) <= 3  # Default should be 3
        assert summary.total_documents == 10  # Total should be 10

    def test_get_category_summary_empty_category(self):
        """Test getting summary for empty category"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Empty", description="Empty category")
        )
        
        summary = self.category_service.get_category_summary(
            category.id, self.test_user_id
        )
        
        assert summary is not None
        assert summary.category.name == "Empty"
        assert summary.category_news == "Empty category"  # Defaults to description
        assert len(summary.representative_documents) == 0
        assert summary.total_documents == 0
    
    def test_get_category_summary_with_custom_news(self):
        """Test getting summary with custom category news"""
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="Tech", description="Tech articles")
        )
        
        # Create and add documents
        doc_ids = []
        for i in range(5):
            doc, _ = self.document_service.create_document(
                DocumentCreate(
                    user_id=self.test_user_id,
                    url=f"https://example.com/{i}",
                    title=f"Article {i}"
                )
            )
            doc_ids.append(doc.id)
        
        self.category_service.add_documents_to_category(
            category.id, doc_ids, self.test_user_id
        )
        
        # Get summary with custom category news
        custom_news = "Latest AI breakthroughs!"
        summary = self.category_service.get_category_summary(
            category.id, self.test_user_id, category_news=custom_news
        )
        
        assert summary is not None
        assert summary.category_news == custom_news  # Should use custom news
        assert summary.category_news != category.description  # Not the default

    def test_get_category_count(self):
        """Test getting category count for a user"""
        # Create categories
        for i in range(3):
            self.category_service.create_category(
                CategoryCreate(user_id=self.test_user_id, name=f"Category{i}")
            )
        
        # Create category for different user
        self.category_service.create_category(
            CategoryCreate(user_id="other_user", name="Other")
        )
        
        count = self.category_service.get_category_count(self.test_user_id)
        assert count == 3
    
    def test_delete_category_success(self):
        """Test successful category deletion"""
        # Create a category
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="ToDelete", description="Will be deleted")
        )
        
        # Verify it exists
        retrieved = self.category_service.get_category_by_id(category.id)
        assert retrieved is not None
        
        # Delete it
        deleted = self.category_service.delete_category(category.id, self.test_user_id)
        assert deleted is True
        
        # Verify it's gone
        retrieved_after = self.category_service.get_category_by_id(category.id)
        assert retrieved_after is None
    
    def test_delete_category_not_found(self):
        """Test deleting a non-existent category"""
        from bson import ObjectId
        fake_id = str(ObjectId())
        
        deleted = self.category_service.delete_category(fake_id, self.test_user_id)
        assert deleted is False
    
    def test_delete_category_wrong_user(self):
        """Test that user cannot delete another user's category"""
        # Create a category for one user
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="UserCategory")
        )
        
        # Try to delete it as a different user
        deleted = self.category_service.delete_category(category.id, "other_user")
        assert deleted is False
        
        # Verify it still exists
        retrieved = self.category_service.get_category_by_id(category.id)
        assert retrieved is not None
    
    def test_delete_category_with_documents(self):
        """Test deleting a category that has documents"""
        # Create a category
        category = self.category_service.create_category(
            CategoryCreate(user_id=self.test_user_id, name="CategoryWithDocs")
        )
        
        # Create and add documents
        doc1 = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/1")
        )[0]
        doc2 = self.document_service.create_document(
            DocumentCreate(user_id=self.test_user_id, url="https://example.com/2")
        )[0]
        
        self.category_service.add_documents_to_category(
            category.id, [doc1.id, doc2.id], self.test_user_id
        )
        
        # Delete the category
        deleted = self.category_service.delete_category(category.id, self.test_user_id)
        assert deleted is True
        
        # Verify category is gone
        retrieved = self.category_service.get_category_by_id(category.id)
        assert retrieved is None
        
        # Verify documents still exist (category deletion should not delete documents)
        doc1_after = self.document_service.get_document_by_id(doc1.id)
        doc2_after = self.document_service.get_document_by_id(doc2.id)
        assert doc1_after is not None
        assert doc2_after is not None

