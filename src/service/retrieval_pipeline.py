from typing import List, Dict, Any
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
import os

# Set OpenAI API key

class RetrievalPipelineService:
    def __init__(self, collection_name: str = "web_embeddings"):
        """Initialize the retrieval pipeline with Qdrant vector store."""
        self.collection_name = collection_name
        # self.client = qdrant_client.QdrantClient(host="localhost", port=6333)
        self.client = qdrant_client.QdrantClient(":memory:")
        self.vector_store = QdrantVectorStore(client=self.client, collection_name=collection_name)
        self.embed_model = OpenAIEmbedding()
    
    def query_vector_store(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Query the vector store for similar content.
        
        Args:
            query: Query string
            top_k: Number of top results to return
            
        Returns:
            Dictionary with query results
        """
        try:
            # Create storage context and index
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=storage_context,
                embed_model=self.embed_model
            )
            
            # Create query engine
            query_engine = index.as_query_engine(similarity_top_k=top_k)
            
            # Execute query
            response = query_engine.query(query)
            
            return {
                "success": True,
                "query": query,
                "response": str(response),
                "top_k": top_k
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during query: {str(e)}",
                "query": query
            }
    
    def get_similar_nodes(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Get similar nodes with metadata from the vector store.
        
        Args:
            query: Query string
            top_k: Number of top results to return
            
        Returns:
            Dictionary with similar nodes and their metadata
        """
        try:
            # Create storage context and index
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=storage_context,
                embed_model=self.embed_model
            )
            
            # Create retriever
            retriever = index.as_retriever(similarity_top_k=top_k)
            
            # Retrieve nodes
            nodes = retriever.retrieve(query)
            
            # Format results with metadata
            results = []
            for node in nodes:
                results.append({
                    "text": node.text,
                    "metadata": node.metadata,
                    "score": node.score if hasattr(node, 'score') else None
                })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_found": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during retrieval: {str(e)}",
                "query": query
            }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                "success": True,
                "collection_name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error getting collection stats: {str(e)}"
            }
