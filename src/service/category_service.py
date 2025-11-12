from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from src.helper.mongodb import mongodb_helper
from src.model.resource import Category, CategoryCreate, CategoryUpdate, CategorySummary, Document
from pymongo.collection import Collection


class CategoryService:
    """Service class for category operations"""
    
    def __init__(self):
        self.collection: Collection = mongodb_helper.get_collection("categories")
        self.documents_collection: Collection = mongodb_helper.get_collection("documents")
    
    def _mongo_doc_to_model(self, doc: Dict[str, Any]) -> Category:
        """Convert MongoDB document to Category model"""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return Category(**doc)
    
    def _mongo_doc_to_document_model(self, doc: Dict[str, Any]) -> Document:
        """Convert MongoDB document to Document model"""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return Document(**doc)
    
    def create_category(self, category: CategoryCreate) -> Category:
        """Create a new category"""
        try:
            # Check if category with same name exists for this user
            existing = self.collection.find_one({
                "user_id": category.user_id,
                "name": category.name
            })
            if existing:
                raise ValueError(f"Category with name '{category.name}' already exists for this user")
            
            # Create new category
            cat_dict = category.model_dump()
            now = datetime.now(timezone.utc)
            cat_dict["created_at"] = now
            cat_dict["updated_at"] = now
            cat_dict["document_ids"] = []
            
            result = self.collection.insert_one(cat_dict)
            
            # Retrieve the created category
            created_cat = self.collection.find_one({"_id": result.inserted_id})
            return self._mongo_doc_to_model(created_cat)
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error creating category: {str(e)}")
    
    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """Get a category by ID"""
        try:
            cat = self.collection.find_one({"_id": ObjectId(category_id)})
            if cat:
                return self._mongo_doc_to_model(cat)
            return None
        except Exception as e:
            raise Exception(f"Error retrieving category: {str(e)}")
    
    def get_all_categories(
        self, 
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Category]:
        """Get all categories for a user"""
        try:
            cursor = self.collection.find({"user_id": user_id}).skip(skip).limit(limit).sort("created_at", -1)
            categories = [self._mongo_doc_to_model(cat) for cat in cursor]
            return categories
        except Exception as e:
            raise Exception(f"Error retrieving categories: {str(e)}")
    
    def update_category(self, category_id: str, update: CategoryUpdate, user_id: str) -> Optional[Category]:
        """Update a category (rename or change description)"""
        try:
            # Check if category exists and belongs to user
            existing = self.collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
            if not existing:
                return None
            
            # If renaming, check if new name already exists
            if update.name and update.name != existing.get("name"):
                name_exists = self.collection.find_one({
                    "user_id": user_id,
                    "name": update.name,
                    "_id": {"$ne": ObjectId(category_id)}
                })
                if name_exists:
                    raise ValueError(f"Category with name '{update.name}' already exists for this user")
            
            # Build update dict with only provided fields
            update_dict = {}
            if update.name is not None:
                update_dict["name"] = update.name
            if update.description is not None:
                update_dict["description"] = update.description
            
            if not update_dict:
                # No changes, return existing
                return self._mongo_doc_to_model(existing)
            
            update_dict["updated_at"] = datetime.now(timezone.utc)
            
            result = self.collection.update_one(
                {"_id": ObjectId(category_id), "user_id": user_id},
                {"$set": update_dict}
            )
            
            if result.modified_count > 0:
                updated_cat = self.collection.find_one({"_id": ObjectId(category_id)})
                return self._mongo_doc_to_model(updated_cat)
            
            return self._mongo_doc_to_model(existing)
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error updating category: {str(e)}")
    
    def add_documents_to_category(self, category_id: str, document_ids: List[str], user_id: str) -> Optional[Category]:
        """Add documents to a category"""
        try:
            # Verify category exists and belongs to user
            category = self.collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
            if not category:
                return None
            
            # Verify all documents exist and belong to user
            doc_object_ids = [ObjectId(doc_id) for doc_id in document_ids]
            docs = list(self.documents_collection.find({
                "_id": {"$in": doc_object_ids},
                "user_id": user_id
            }))
            
            if len(docs) != len(document_ids):
                raise ValueError("Some documents not found or don't belong to user")
            
            # Add documents to category (use $addToSet to avoid duplicates)
            result = self.collection.update_one(
                {"_id": ObjectId(category_id), "user_id": user_id},
                {
                    "$addToSet": {"document_ids": {"$each": document_ids}},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            
            updated_cat = self.collection.find_one({"_id": ObjectId(category_id)})
            return self._mongo_doc_to_model(updated_cat)
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error adding documents to category: {str(e)}")
    
    def remove_documents_from_category(self, category_id: str, document_ids: List[str], user_id: str) -> Optional[Category]:
        """Remove documents from a category"""
        try:
            # Verify category exists and belongs to user
            category = self.collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
            if not category:
                return None
            
            # Remove documents from category
            result = self.collection.update_one(
                {"_id": ObjectId(category_id), "user_id": user_id},
                {
                    "$pull": {"document_ids": {"$in": document_ids}},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            
            updated_cat = self.collection.find_one({"_id": ObjectId(category_id)})
            return self._mongo_doc_to_model(updated_cat)
        except Exception as e:
            raise Exception(f"Error removing documents from category: {str(e)}")
    
    def get_documents_in_category(
        self,
        category_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get all documents in a category"""
        try:
            # Get category
            category = self.collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
            if not category:
                return []
            
            document_ids = category.get("document_ids", [])
            if not document_ids:
                return []
            
            # Convert to ObjectIds and get documents
            doc_object_ids = [ObjectId(doc_id) for doc_id in document_ids]
            
            # Apply pagination
            cursor = self.documents_collection.find({
                "_id": {"$in": doc_object_ids}
            }).skip(skip).limit(limit).sort("created_at", -1)
            
            documents = [self._mongo_doc_to_document_model(doc) for doc in cursor]
            return documents
        except Exception as e:
            raise Exception(f"Error retrieving documents in category: {str(e)}")
    
    def get_category_summary(
        self,
        category_id: str,
        user_id: str,
        doc_limit: int = 3,
        category_news: Optional[str] = None
    ) -> Optional[CategorySummary]:
        """Get category summary with a subset of representative documents
        
        Args:
            category_id: Category ID
            user_id: User ID for authorization
            doc_limit: Number of representative documents to include (default 3)
            category_news: Override for category news (defaults to category description)
        """
        try:
            # Get category
            category = self.collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
            if not category:
                return None
            
            category_model = self._mongo_doc_to_model(category)
            document_ids = category.get("document_ids", [])
            total_documents = len(document_ids)
            
            # Get subset of representative documents (most recent by default)
            representative_documents = []
            if document_ids:
                doc_object_ids = [ObjectId(doc_id) for doc_id in document_ids[:doc_limit]]
                cursor = self.documents_collection.find({
                    "_id": {"$in": doc_object_ids}
                }).limit(doc_limit).sort("created_at", -1)
                
                representative_documents = [self._mongo_doc_to_document_model(doc) for doc in cursor]
            
            # Use provided category_news or default to category description
            news = category_news if category_news is not None else category_model.description
            
            return CategorySummary(
                category=category_model,
                category_news=news,
                representative_documents=representative_documents,
                total_documents=total_documents
            )
        except Exception as e:
            raise Exception(f"Error retrieving category summary: {str(e)}")
    
    def get_category_count(self, user_id: str) -> int:
        """Get total category count for a user"""
        try:
            return self.collection.count_documents({"user_id": user_id})
        except Exception as e:
            raise Exception(f"Error counting categories: {str(e)}")
    
    def delete_category(self, category_id: str, user_id: str) -> bool:
        """Delete a category
        
        Args:
            category_id: Category ID to delete
            user_id: User ID for authorization
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # Verify category exists and belongs to user
            category = self.collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
            if not category:
                return False
            
            # Delete the category
            result = self.collection.delete_one({"_id": ObjectId(category_id), "user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Error deleting category: {str(e)}")

