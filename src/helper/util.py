"""
Utility functions for web crawling, text processing, and embeddings.
Provides tools for content extraction and document chunking.
"""
import logging
from typing import List

from crawl4ai import AsyncWebCrawler
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser
from llama_index.core.schema import Document, BaseNode
from llama_index.embeddings.openai import OpenAIEmbedding


logger = logging.getLogger(__name__)


async def get_text_from_url(url: str) -> str:
    """
    Extract text content from a URL using web crawling.
    
    Args:
        url: The URL to crawl and extract content from
        
    Returns:
        Extracted text content in markdown format
        
    Raises:
        Exception: If crawling fails or URL is invalid
    """
    try:
        logger.info(f"Crawling URL: {url}")
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url)
            logger.info(f"Successfully crawled URL: {url}")
            return result.markdown
    except Exception as e:
        logger.error(f"Error crawling URL {url}: {str(e)}", exc_info=True)
        raise


def split_text(text: str, split_type: str = "recursive") -> List[BaseNode]:
    """
    Split text into chunks using different strategies.
    
    Args:
        text: The text content to split
        split_type: Splitting strategy - "recursive" or "semantic"
        
    Returns:
        List of text nodes/chunks
        
    Raises:
        ValueError: If split_type is invalid
    """
    try:
        logger.info(f"Splitting text using {split_type} strategy")
        
        if split_type == "recursive":
            # Use sentence-based recursive splitting
            text_splitter = SentenceSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            nodes = text_splitter.get_nodes_from_documents([Document(text=text)])
            
        elif split_type == "semantic":
            # Use semantic similarity-based splitting
            embed_model = OpenAIEmbedding()
            text_splitter = SemanticSplitterNodeParser(
                buffer_size=1,
                breakpoint_percentile_threshold=95,
                embed_model=embed_model
            )
            nodes = text_splitter.get_nodes_from_documents([Document(text=text)])
            
        else:
            raise ValueError(
                f"Invalid split type: {split_type}. "
                "Must be 'recursive' or 'semantic'"
            )
        
        logger.info(f"Created {len(nodes)} text chunks")
        return list(nodes)
        
    except Exception as e:
        logger.error(f"Error splitting text: {str(e)}", exc_info=True)
        raise


def get_embedding(nodes: List[BaseNode]) -> List[BaseNode]:
    """
    Generate embeddings for text nodes.
    
    Args:
        nodes: List of text nodes to generate embeddings for
        
    Returns:
        List of nodes with embeddings attached
        
    Raises:
        Exception: If embedding generation fails
    """
    try:
        logger.info(f"Generating embeddings for {len(nodes)} nodes")
        embed_model = OpenAIEmbedding()
        
        for idx, node in enumerate(nodes):
            # Get text content with metadata
            content = node.get_content(metadata_mode="all")
            
            # Generate embedding
            node_embedding = embed_model.get_text_embedding(content)
            node.embedding = node_embedding
            
            if (idx + 1) % 10 == 0:
                logger.info(f"Generated embeddings for {idx + 1}/{len(nodes)} nodes")
        
        logger.info(f"Successfully generated embeddings for all {len(nodes)} nodes")
        return nodes
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}", exc_info=True)
        raise
