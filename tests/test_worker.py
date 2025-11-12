"""
Unit tests for Document Worker
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.worker import DocumentWorker
from src.model.resource import ProcessingStatus, DocumentCreate
from src.service.document_service import DocumentService
from src.service.queue_manager import QueueManager
import os
from pathlib import Path


class TestDocumentWorker:
    """Test cases for DocumentWorker"""
    
    @pytest.fixture(autouse=True)
    def setup(self, clean_documents_collection):
        """Setup for each test"""
        self.document_service = DocumentService()
        self.test_queue_file = ".test_worker_queue.json"
        self.queue = QueueManager(queue_file=self.test_queue_file)
        self.queue.clear()
        yield
        # Cleanup
        if Path(self.test_queue_file).exists():
            os.remove(self.test_queue_file)
    
    def test_worker_initialization(self):
        """Test worker initializes correctly"""
        worker = DocumentWorker()
        assert worker.running is True
        assert worker.poll_interval == 2
        assert worker.document_service is not None
    
    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """Test successful document processing"""
        # Create a test document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, _ = self.document_service.create_document(doc_create)
        
        # Process the document
        worker = DocumentWorker()
        
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
            document_id=created_doc.id,
            user_id=created_doc.user_id,
            metadata={"url": created_doc.url}
        )
        
        assert result is True
        
        # Verify status was updated to COMPLETE
        updated_doc = self.document_service.get_document_by_id(created_doc.id)
        assert updated_doc.processing_status == ProcessingStatus.COMPLETE
    
    @pytest.mark.asyncio
    async def test_process_document_updates_to_in_progress(self):
        """Test that document status is updated to IN_PROGRESS during processing"""
        # Create a test document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, _ = self.document_service.create_document(doc_create)
        
        worker = DocumentWorker()
        
        # Track status changes
        statuses = []
        original_update = self.document_service.update_processing_status
        
        def mock_update(document_id, status):
            statuses.append(status)
            return original_update(document_id, status)
        
        # Mock the document processor to return success
        mock_result = {
            "success": True,
            "document_id": created_doc.id,
            "summary": "Test summary",
            "categorization": {"action": "create_new", "category_name": "Test"},
            "category_id": "cat123"
        }
        worker.document_processor.process_document = AsyncMock(return_value=mock_result)
        
        with patch.object(self.document_service, 'update_processing_status', side_effect=mock_update):
            worker.document_service = self.document_service
            await worker.process_document(
                document_id=created_doc.id,
                user_id=created_doc.user_id,
                metadata={}
            )
        
        # Verify status progression
        assert ProcessingStatus.IN_PROGRESS in statuses
        assert ProcessingStatus.COMPLETE in statuses
    
    @pytest.mark.asyncio
    async def test_process_document_handles_errors(self):
        """Test that worker handles errors gracefully"""
        worker = DocumentWorker()
        
        # Mock the document processor to return failure
        mock_result = {
            "success": False,
            "message": "Document not found"
        }
        worker.document_processor.process_document = AsyncMock(return_value=mock_result)
        
        # Try to process a non-existent document
        result = await worker.process_document(
            document_id="nonexistent123",
            user_id="test_user",
            metadata={}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_worker_processes_queued_document(self):
        """Test that worker picks up and processes queued documents"""
        # Create a test document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, _ = self.document_service.create_document(doc_create)
        
        # Enqueue the document
        self.queue.enqueue(
            document_id=created_doc.id,
            user_id=created_doc.user_id,
            metadata={"url": created_doc.url}
        )
        
        # Process from queue
        worker = DocumentWorker()
        
        # Mock the document processor to return success
        mock_result = {
            "success": True,
            "document_id": created_doc.id,
            "summary": "Test summary",
            "categorization": {"action": "create_new", "category_name": "Test"},
            "category_id": "cat123"
        }
        worker.document_processor.process_document = AsyncMock(return_value=mock_result)
        
        with patch.object(worker, 'running', True):
            with patch('src.service.queue_manager.queue_manager', self.queue):
                # Get item from queue
                item = self.queue.dequeue()
                if item:
                    await worker.process_document(
                        document_id=item['document_id'],
                        user_id=item['user_id'],
                        metadata=item['metadata']
                    )
        
        # Verify document was processed
        updated_doc = self.document_service.get_document_by_id(created_doc.id)
        assert updated_doc.processing_status == ProcessingStatus.COMPLETE
        
        # Verify queue is empty
        assert self.queue.size() == 0


class TestDocumentServiceProcessingStatus:
    """Test cases for DocumentService processing status methods"""
    
    @pytest.fixture(autouse=True)
    def setup(self, clean_documents_collection):
        """Setup for each test"""
        self.service = DocumentService()
    
    def test_update_processing_status(self):
        """Test updating document processing status"""
        # Create a document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, _ = self.service.create_document(doc_create)
        
        # Verify initial status
        assert created_doc.processing_status == ProcessingStatus.QUEUED
        
        # Update to IN_PROGRESS
        result = self.service.update_processing_status(
            created_doc.id,
            ProcessingStatus.IN_PROGRESS
        )
        assert result is True
        
        # Verify status was updated
        updated_doc = self.service.get_document_by_id(created_doc.id)
        assert updated_doc.processing_status == ProcessingStatus.IN_PROGRESS
        
        # Update to COMPLETE
        result = self.service.update_processing_status(
            created_doc.id,
            ProcessingStatus.COMPLETE
        )
        assert result is True
        
        # Verify status was updated
        final_doc = self.service.get_document_by_id(created_doc.id)
        assert final_doc.processing_status == ProcessingStatus.COMPLETE
    
    def test_update_processing_status_nonexistent_document(self):
        """Test updating status of nonexistent document returns False"""
        from bson import ObjectId
        fake_id = str(ObjectId())
        
        # This should not raise but return False
        result = self.service.update_processing_status(
            fake_id,
            ProcessingStatus.COMPLETE
        )
        assert result is False
    
    def test_create_document_sets_queued_status(self):
        """Test that newly created documents have QUEUED status"""
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, was_created = self.service.create_document(doc_create)
        
        assert was_created is True
        assert created_doc.processing_status == ProcessingStatus.QUEUED
    
    def test_update_processing_status_to_failed(self):
        """Test updating document status to FAILED"""
        # Create a document
        doc_create = DocumentCreate(
            user_id="test_user",
            url="https://example.com",
            title="Test Document"
        )
        created_doc, _ = self.service.create_document(doc_create)
        
        # Update to FAILED
        result = self.service.update_processing_status(
            created_doc.id,
            ProcessingStatus.FAILED
        )
        assert result is True
        
        # Verify status was updated
        updated_doc = self.service.get_document_by_id(created_doc.id)
        assert updated_doc.processing_status == ProcessingStatus.FAILED

