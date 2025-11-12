"""
Queue Manager for handling document processing queue
Uses a simple file-based queue for communication between main app and worker process
"""
import os
import json
import fcntl
import time
from pathlib import Path
from typing import Optional, Dict, Any


class QueueManager:
    """Simple file-based queue manager for document processing"""
    
    def __init__(self, queue_file: str = ".document_queue.json"):
        """Initialize the queue manager"""
        self.queue_file = Path(queue_file)
        self._ensure_queue_file_exists()
    
    def _ensure_queue_file_exists(self):
        """Ensure the queue file exists"""
        if not self.queue_file.exists():
            with open(self.queue_file, 'w') as f:
                json.dump([], f)
    
    def _read_queue(self) -> list:
        """Read the queue from file with file locking"""
        max_retries = 5
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                with open(self.queue_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        content = f.read()
                        if not content:
                            return []
                        return json.loads(content)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (IOError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return []
        return []
    
    def _write_queue(self, queue: list):
        """Write the queue to file with file locking"""
        max_retries = 5
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                with open(self.queue_file, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(queue, f, indent=2)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return
            except IOError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise
    
    def enqueue(self, document_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a document to the processing queue"""
        queue = self._read_queue()
        
        # Check if document is already in queue
        if any(item['document_id'] == document_id for item in queue):
            return False
        
        item = {
            'document_id': document_id,
            'user_id': user_id,
            'queued_at': time.time(),
            'metadata': metadata or {}
        }
        
        queue.append(item)
        self._write_queue(queue)
        return True
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """Remove and return the first item from the queue"""
        queue = self._read_queue()
        
        if not queue:
            return None
        
        item = queue.pop(0)
        self._write_queue(queue)
        return item
    
    def peek(self) -> Optional[Dict[str, Any]]:
        """Peek at the first item in the queue without removing it"""
        queue = self._read_queue()
        return queue[0] if queue else None
    
    def size(self) -> int:
        """Get the current queue size"""
        queue = self._read_queue()
        return len(queue)
    
    def clear(self):
        """Clear the entire queue"""
        self._write_queue([])
    
    def get_all(self) -> list:
        """Get all items in the queue"""
        return self._read_queue()


# Singleton instance
queue_manager = QueueManager()

