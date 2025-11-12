"""
Integration tests for background document processing
Tests the full flow from document creation to processing
"""
import pytest
import time
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.route import app
from src.service.document_service import DocumentService
from src.service.queue_manager import QueueManager
from src.model.resource import DocumentCreate, ProcessingStatus
from src.worker import DocumentWorker


class TestBackgroundProcessingIntegration:
    """Integration tests for background processing"""
    
    @pytest.fixture(autouse=True)
    def setup(self, clean_documents_collection):
        """Setup for each test"""
        self.client = TestClient(app)
        self.document_service = DocumentService()
        self.test_queue_file = ".test_integration_queue.json"
        self.queue = QueueManager(queue_file=self.test_queue_file)
        self.queue.clear()
        yield
        # Cleanup
        if Path(self.test_queue_file).exists():
            os.remove(self.test_queue_file)
    
    def test_document_creation_sets_queued_status(self):
        """Test that document creation sets status to QUEUED"""
        # Mock the queue manager to use test queue
        with patch('src.api.route.queue_manager', self.queue):
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
        assert data['processing_status'] == ProcessingStatus.QUEUED.value
        assert data['_id'] is not None
    
    def test_document_creation_enqueues_for_processing(self):
        """Test that document creation adds item to queue"""
        with patch('src.api.route.queue_manager', self.queue):
            response = self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": "https://example.com",
                    "title": "Test Document"
                }
            )
        
        assert response.status_code == 201
        
        # Verify item was added to queue
        assert self.queue.size() == 1
        
        item = self.queue.peek()
        assert item is not None
        assert item['user_id'] == "test_user"
        assert item['metadata']['url'] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_full_processing_flow(self):
        """Test complete flow from creation to processing"""
        # Create document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, was_created = self.document_service.create_document(doc_create)
        
        # Verify initial status and was created
        assert was_created is True
        assert created_doc.processing_status == ProcessingStatus.QUEUED
        
        # Enqueue
        self.queue.enqueue(
            document_id=created_doc.id,
            user_id=created_doc.user_id,
            metadata={"url": created_doc.url}
        )
        
        # Process with worker
        worker = DocumentWorker()
        item = self.queue.dequeue()
        
        # Mock the document processor to return success
        mock_result = {
            "success": True,
            "document_id": created_doc.id,
            "summary": "Test summary",
            "categorization": {"action": "create_new", "category_name": "Test"},
            "category_id": "cat123"
        }
        worker.document_processor.process_document = AsyncMock(return_value=mock_result)
        
        result = await worker.process_document(
            document_id=item['document_id'],
            user_id=item['user_id'],
            metadata=item['metadata']
        )
        
        assert result is True
        
        # Verify final status
        final_doc = self.document_service.get_document_by_id(created_doc.id)
        assert final_doc.processing_status == ProcessingStatus.COMPLETE
    
    @pytest.mark.asyncio
    async def test_multiple_documents_processing(self):
        """Test processing multiple documents"""
        # Create multiple documents
        doc_ids = []
        for i in range(3):
            doc_create = DocumentCreate(
                user_id=f"user_{i}",
                url=f"https://example.com/{i}",
                title=f"Document {i}"
            )
            created_doc, _ = self.document_service.create_document(doc_create)
            doc_ids.append(created_doc.id)
            
            self.queue.enqueue(
                document_id=created_doc.id,
                user_id=created_doc.user_id,
                metadata={"url": created_doc.url}
            )
        
        # Process all documents
        worker = DocumentWorker()
        
        # Mock the document processor to return success
        mock_result = {
            "success": True,
            "summary": "Test summary",
            "categorization": {"action": "create_new", "category_name": "Test"},
            "category_id": "cat123"
        }
        worker.document_processor.process_document = AsyncMock(return_value=mock_result)
        
        while self.queue.size() > 0:
            item = self.queue.dequeue()
            await worker.process_document(
                document_id=item['document_id'],
                user_id=item['user_id'],
                metadata=item['metadata']
            )
        
        # Verify all documents were processed
        for doc_id in doc_ids:
            doc = self.document_service.get_document_by_id(doc_id)
            assert doc.processing_status == ProcessingStatus.COMPLETE
    
    def test_api_returns_immediately_while_processing_queued(self):
        """Test that API returns immediately and processing happens in background"""
        with patch('src.api.route.queue_manager', self.queue):
            # Measure response time
            start_time = time.time()
            response = self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": "https://example.com",
                    "title": "Test Document"
                }
            )
            end_time = time.time()
            
            response_time = end_time - start_time
        
        # API should return quickly (under 1 second)
        assert response_time < 1.0
        assert response.status_code == 201
        
        # Document should be in QUEUED state
        data = response.json()
        assert data['processing_status'] == ProcessingStatus.QUEUED.value
        
        # Queue should have the document
        assert self.queue.size() == 1
    
    def test_get_document_shows_current_processing_status(self):
        """Test that GET endpoint shows current processing status"""
        # Create document
        with patch('src.api.route.queue_manager', self.queue):
            create_response = self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": "https://example.com",
                    "title": "Test Document"
                }
            )
        
        doc_id = create_response.json()['_id']
        
        # Get document - should show QUEUED
        get_response = self.client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()['processing_status'] == ProcessingStatus.QUEUED.value
        
        # Update to IN_PROGRESS
        self.document_service.update_processing_status(
            doc_id,
            ProcessingStatus.IN_PROGRESS
        )
        
        # Get document again - should show IN_PROGRESS
        get_response = self.client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()['processing_status'] == ProcessingStatus.IN_PROGRESS.value
        
        # Update to COMPLETE
        self.document_service.update_processing_status(
            doc_id,
            ProcessingStatus.COMPLETE
        )
        
        # Get document again - should show COMPLETE
        get_response = self.client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 200
        assert get_response.json()['processing_status'] == ProcessingStatus.COMPLETE.value
    
    def test_list_documents_shows_processing_status(self):
        """Test that listing documents includes processing status"""
        # Create multiple documents with different statuses
        with patch('src.api.route.queue_manager', self.queue):
            # Document 1 - will stay QUEUED
            self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": "https://example.com/1",
                    "title": "Document 1"
                }
            )
            
            # Document 2 - will be IN_PROGRESS
            response2 = self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": "https://example.com/2",
                    "title": "Document 2"
                }
            )
            doc2_id = response2.json()['_id']
            self.document_service.update_processing_status(
                doc2_id,
                ProcessingStatus.IN_PROGRESS
            )
            
            # Document 3 - will be COMPLETE
            response3 = self.client.post(
                "/documents",
                json={
                    "user_id": "test_user",
                    "url": "https://example.com/3",
                    "title": "Document 3"
                }
            )
            doc3_id = response3.json()['_id']
            self.document_service.update_processing_status(
                doc3_id,
                ProcessingStatus.COMPLETE
            )
        
        # Get all documents
        list_response = self.client.get("/documents?user_id=test_user")
        assert list_response.status_code == 200
        
        documents = list_response.json()
        assert len(documents) == 3
        
        # Verify each document has processing_status field
        for doc in documents:
            assert 'processing_status' in doc
            assert doc['processing_status'] in [
                ProcessingStatus.QUEUED.value,
                ProcessingStatus.IN_PROGRESS.value,
                ProcessingStatus.COMPLETE.value
            ]
    
    @pytest.mark.asyncio
    async def test_worker_handles_failed_processing(self):
        """Test that worker handles processing failures gracefully"""
        # Create a document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, _ = self.document_service.create_document(doc_create)
        
        worker = DocumentWorker()
        
        # Mock the document processor to raise an exception
        worker.document_processor.process_document = AsyncMock(side_effect=Exception("Processing error"))
        
        result = await worker.process_document(
            document_id=created_doc.id,
            user_id=created_doc.user_id,
            metadata={}
        )
        
        assert result is False
        
        # Verify status was set to FAILED
        doc = self.document_service.get_document_by_id(created_doc.id)
        assert doc.processing_status == ProcessingStatus.FAILED

