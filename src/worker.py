"""
Background worker process for document processing.
Continuously polls the queue and processes documents asynchronously.
"""
import os
import sys
import time
import signal
import logging
import asyncio

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.service.queue_manager import queue_manager
from src.service.document_service import DocumentService
from src.service.document_processor import DocumentProcessor
from src.model.resource import ProcessingStatus


# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentWorker:
    """
    Worker class for processing documents from the queue.
    Handles graceful shutdown and error recovery.
    """
    
    def __init__(self):
        """Initialize worker with required services."""
        self.document_service = DocumentService()
        self.document_processor = DocumentProcessor()
        self.running = True
        self.poll_interval = settings.worker_poll_interval
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)
    
    def _shutdown_handler(self, signum, frame):
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}. Stopping worker...")
        self.running = False
    
    async def process_document(
        self,
        document_id: str,
        user_id: str,
        metadata: dict
    ) -> bool:
        """
        Process a single document: summarize and categorize.
        
        Args:
            document_id: ID of the document to process
            user_id: User ID who owns the document
            metadata: Additional metadata about the document
            
        Returns:
            True if processing succeeded, False otherwise
        """
        logger.info(
            f"Processing document {document_id} for user {user_id}"
        )
        
        try:
            # Update status to IN_PROGRESS
            self.document_service.update_processing_status(
                document_id=document_id,
                status=ProcessingStatus.IN_PROGRESS
            )
            logger.info(f"Document {document_id} status: IN_PROGRESS")
            
            # Process the document (summarize and categorize)
            result = await self.document_processor.process_document(
                document_id=document_id,
                user_id=user_id
            )
            
            if result["success"]:
                logger.info(f"Successfully processed document {document_id}")
                logger.info(f"Summary length: {len(result.get('summary', ''))}")
                logger.info(f"Categorization: {result.get('categorization')}")
                logger.info(f"Category ID: {result.get('category_id')}")
                
                # Update status to COMPLETE
                self.document_service.update_processing_status(
                    document_id=document_id,
                    status=ProcessingStatus.COMPLETE
                )
                logger.info(f"Document {document_id} status: COMPLETE")
                return True
                
            else:
                logger.error(
                    f"Processing failed for document {document_id}: "
                    f"{result.get('message')}"
                )
                self.document_service.update_processing_status(
                    document_id=document_id,
                    status=ProcessingStatus.FAILED
                )
                logger.info(f"Document {document_id} status: FAILED")
                return False
            
        except Exception as e:
            logger.error(
                f"Error processing document {document_id}: {str(e)}",
                exc_info=True
            )
            
            try:
                self.document_service.update_processing_status(
                    document_id=document_id,
                    status=ProcessingStatus.FAILED
                )
                logger.info(f"Document {document_id} status: FAILED")
            except Exception as update_error:
                logger.error(
                    f"Error updating status to FAILED: {str(update_error)}",
                    exc_info=True
                )
            
            return False
    
    def run(self):
        """
        Main worker loop.
        Continuously polls the queue and processes documents.
        """
        logger.info("=" * 60)
        logger.info("Document worker started")
        logger.info(f"App: {settings.app_name} v{settings.app_version}")
        logger.info(f"Polling interval: {self.poll_interval} seconds")
        logger.info("=" * 60)
        
        while self.running:
            try:
                # Check queue for new documents
                item = queue_manager.dequeue()
                
                if item:
                    document_id = item.get('document_id')
                    user_id = item.get('user_id')
                    metadata = item.get('metadata', {})
                    
                    logger.info(f"Found document in queue: {document_id}")
                    
                    # Run the async process_document in a new event loop
                    asyncio.run(
                        self.process_document(document_id, user_id, metadata)
                    )
                else:
                    # No items in queue, wait before polling again
                    logger.debug("Queue is empty, waiting...")
                    time.sleep(self.poll_interval)
                    
            except KeyboardInterrupt:
                logger.info("Worker interrupted by user")
                self.running = False
                
            except Exception as e:
                logger.error(
                    f"Error in worker loop: {str(e)}",
                    exc_info=True
                )
                time.sleep(self.poll_interval)
        
        logger.info("=" * 60)
        logger.info("Document worker stopped")
        logger.info("=" * 60)


def main():
    """Main entry point for the worker process."""
    logger.info("Starting document processing worker...")
    
    try:
        worker = DocumentWorker()
        worker.run()
    except Exception as e:
        logger.error(
            f"Fatal error in worker: {str(e)}",
            exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
