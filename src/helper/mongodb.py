from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MongoDBHelper:
    """Helper class for MongoDB operations"""
    
    _instance: Optional['MongoDBHelper'] = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBHelper, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "dossier")
        
        try:
            self._client = MongoClient(mongodb_uri)
            self._database = self._client[database_name]
            # Test connection
            self._client.server_info()
            print(f"Successfully connected to MongoDB: {database_name}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise
    
    def get_database(self) -> Database:
        """Get database instance"""
        if self._database is None:
            self._connect()
        return self._database
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get collection instance"""
        db = self.get_database()
        return db[collection_name]
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            print("MongoDB connection closed")


# Singleton instance
mongodb_helper = MongoDBHelper()

