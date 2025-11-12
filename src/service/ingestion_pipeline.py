import asyncio
import hashlib
import json
from typing import List, Dict, Any
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import BaseNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.extractors import TitleExtractor
from llama_index.core.node_parser import SentenceSplitter
import os
from src.model.resource import WebResource
from src.helper.util import get_text_from_url, split_text

# Set OpenAI API key

class IngestionPipelineService:
    def __init__(self, collection_name: str = "web_embeddings"):
        """Initialize the ingestion pipeline with Qdrant vector store."""
        self.collection_name = collection_name
        self.client = qdrant_client.QdrantClient(host="localhost", port=6333)
        self.vector_store = QdrantVectorStore(client=self.client, collection_name=collection_name)
        self.embed_model = OpenAIEmbedding()
        
        # Cache to store processed content hashes
        self.processed_cache = set()
        
        # Initialize ingestion pipeline
        self.pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=1000, chunk_overlap=200),
                TitleExtractor(),
                self.embed_model,
            ],
            vector_store=self.vector_store,
        )
    
    def _generate_content_hash(self, text: str) -> str:
        """Generate a hash for the input text to check for duplicates."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _add_metadata_to_nodes(self, nodes: List[BaseNode], resource: WebResource) -> List[BaseNode]:
        """Add metadata to nodes with first character as name key."""

        for idx, node in enumerate(nodes):
            # Add metadata
            node.metadata.update({
                "name": resource.user_id,
                "url": resource.web_url,
                "chunk_index": idx,
                "total_chunks": len(nodes),
            })
        
        return nodes

    
    def ingest_resource(self, resource: WebResource, split_type: str = "recursive") -> Dict[str, Any]:
        """
        Ingest text into the vector store with caching and metadata.
        
        Args:
            text: Input text to ingest
            split_type: Type of text splitting ("recursive" or "semantic")
            
        Returns:
            Dictionary with ingestion results
        """
        text = asyncio.run(get_text_from_url(url=resource.web_url))
        if not text or not text.strip():
            return {"success": False, "message": "Empty text provided"}
        
        # Generate content hash for caching
        content_hash = self._generate_content_hash(text)
        
        # Check cache to avoid duplicates
        if content_hash in self.processed_cache:
            return {
                "success": True, 
                "message": "Content already processed (cached)",
                "content_hash": content_hash,
                "cached": True
            }
        
        try:
            # Split text using the util function
            nodes = split_text(text=text, split_type=split_type)
            
            # Add metadata to nodes
            nodes_with_metadata = self._add_metadata_to_nodes(nodes, resource)
            
            # Add embeddings to nodes
            for node in nodes_with_metadata:
                if not hasattr(node, 'embedding') or node.embedding is None:
                    node.embedding = self.embed_model.get_text_embedding(
                        node.get_content(metadata_mode="all")
                    )
            
            # Persist nodes in Qdrant
            self.vector_store.add(nodes_with_metadata)
            
            # Add to cache
            self.processed_cache.add(content_hash)
            
            return {
                "success": True,
                "message": f"Successfully ingested {len(nodes_with_metadata)} chunks",
                "content_hash": content_hash,
                "chunks_created": len(nodes_with_metadata),
                "cached": False
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during ingestion: {str(e)}",
                "content_hash": content_hash
            }
    
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the processed cache."""
        return {
            "cache_size": len(self.processed_cache),
            "cached_hashes": list(self.processed_cache)
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear the processed cache."""
        cache_size = len(self.processed_cache)
        self.processed_cache.clear()
        return {
            "success": True,
            "message": f"Cleared {cache_size} cached entries"
        }
