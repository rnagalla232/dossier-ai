"""
Pytest configuration and fixtures for document API tests
"""
import pytest
import os
from typing import Generator
from pymongo import MongoClient
from pymongo.database import Database


# Set test environment variables
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["MONGODB_DATABASE"] = "dossier"


@pytest.fixture(scope="session")
def mongodb_client() -> Generator[MongoClient, None, None]:
    """Create MongoDB client for testing"""
    client = MongoClient("mongodb://localhost:27017")
    yield client
    client.close()


@pytest.fixture(scope="session")
def test_db(mongodb_client: MongoClient) -> Database:
    """Get test database"""
    return mongodb_client["dossier"]


@pytest.fixture(scope="function")
def clean_documents_collection(test_db: Database):
    """Clean documents collection before each test"""
    test_db.documents.delete_many({})
    yield
    # Cleanup after test as well
    test_db.documents.delete_many({})


@pytest.fixture(scope="function")
def clean_categories_collection(test_db: Database):
    """Clean categories collection before each test"""
    test_db.categories.delete_many({})
    yield
    # Cleanup after test as well
    test_db.categories.delete_many({})


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for API testing"""
    return "http://localhost:8000"

