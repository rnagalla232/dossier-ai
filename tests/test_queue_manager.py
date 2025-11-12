"""
Unit tests for QueueManager
"""
import pytest
import os
from pathlib import Path
from src.service.queue_manager import QueueManager


class TestQueueManager:
    """Test cases for QueueManager"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        # Use a test-specific queue file
        self.test_queue_file = ".test_document_queue.json"
        self.queue = QueueManager(queue_file=self.test_queue_file)
        yield
        # Cleanup
        if Path(self.test_queue_file).exists():
            os.remove(self.test_queue_file)
    
    def test_queue_initialization(self):
        """Test that queue file is created on initialization"""
        assert Path(self.test_queue_file).exists()
    
    def test_enqueue_document(self):
        """Test enqueueing a document"""
        result = self.queue.enqueue(
            document_id="doc123",
            user_id="user456",
            metadata={"url": "https://example.com"}
        )
        
        assert result is True
        assert self.queue.size() == 1
    
    def test_enqueue_duplicate_document(self):
        """Test that duplicate documents are not enqueued"""
        # Enqueue first time
        self.queue.enqueue(
            document_id="doc123",
            user_id="user456"
        )
        
        # Try to enqueue again
        result = self.queue.enqueue(
            document_id="doc123",
            user_id="user456"
        )
        
        assert result is False
        assert self.queue.size() == 1
    
    def test_dequeue_document(self):
        """Test dequeuing a document"""
        # Enqueue a document
        self.queue.enqueue(
            document_id="doc123",
            user_id="user456",
            metadata={"url": "https://example.com"}
        )
        
        # Dequeue it
        item = self.queue.dequeue()
        
        assert item is not None
        assert item['document_id'] == "doc123"
        assert item['user_id'] == "user456"
        assert item['metadata']['url'] == "https://example.com"
        assert 'queued_at' in item
        assert self.queue.size() == 0
    
    def test_dequeue_empty_queue(self):
        """Test dequeuing from empty queue returns None"""
        item = self.queue.dequeue()
        assert item is None
    
    def test_dequeue_fifo_order(self):
        """Test that dequeue follows FIFO order"""
        # Enqueue multiple documents
        self.queue.enqueue("doc1", "user1")
        self.queue.enqueue("doc2", "user2")
        self.queue.enqueue("doc3", "user3")
        
        # Dequeue and verify order
        item1 = self.queue.dequeue()
        assert item1['document_id'] == "doc1"
        
        item2 = self.queue.dequeue()
        assert item2['document_id'] == "doc2"
        
        item3 = self.queue.dequeue()
        assert item3['document_id'] == "doc3"
    
    def test_peek_document(self):
        """Test peeking at first document without removing it"""
        # Enqueue documents
        self.queue.enqueue("doc1", "user1")
        self.queue.enqueue("doc2", "user2")
        
        # Peek
        item = self.queue.peek()
        
        assert item is not None
        assert item['document_id'] == "doc1"
        assert self.queue.size() == 2  # Size should not change
    
    def test_peek_empty_queue(self):
        """Test peeking at empty queue returns None"""
        item = self.queue.peek()
        assert item is None
    
    def test_queue_size(self):
        """Test getting queue size"""
        assert self.queue.size() == 0
        
        self.queue.enqueue("doc1", "user1")
        assert self.queue.size() == 1
        
        self.queue.enqueue("doc2", "user2")
        assert self.queue.size() == 2
        
        self.queue.dequeue()
        assert self.queue.size() == 1
    
    def test_clear_queue(self):
        """Test clearing the queue"""
        # Enqueue multiple documents
        self.queue.enqueue("doc1", "user1")
        self.queue.enqueue("doc2", "user2")
        self.queue.enqueue("doc3", "user3")
        
        assert self.queue.size() == 3
        
        # Clear
        self.queue.clear()
        
        assert self.queue.size() == 0
        assert self.queue.peek() is None
    
    def test_get_all_items(self):
        """Test getting all items in queue"""
        # Enqueue documents
        self.queue.enqueue("doc1", "user1", {"title": "Doc 1"})
        self.queue.enqueue("doc2", "user2", {"title": "Doc 2"})
        
        all_items = self.queue.get_all()
        
        assert len(all_items) == 2
        assert all_items[0]['document_id'] == "doc1"
        assert all_items[1]['document_id'] == "doc2"
    
    def test_enqueue_with_metadata(self):
        """Test enqueueing with metadata"""
        metadata = {
            "url": "https://example.com",
            "title": "Test Document",
            "extra": "data"
        }
        
        self.queue.enqueue(
            document_id="doc123",
            user_id="user456",
            metadata=metadata
        )
        
        item = self.queue.dequeue()
        assert item['metadata'] == metadata
    
    def test_enqueue_without_metadata(self):
        """Test enqueueing without metadata"""
        self.queue.enqueue(
            document_id="doc123",
            user_id="user456"
        )
        
        item = self.queue.dequeue()
        assert item['metadata'] == {}

