from typing import List
from crawl4ai import AsyncWebCrawler
import asyncio
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import Document
from llama_index.core.schema import BaseNode
from llama_index.embeddings.openai import OpenAIEmbedding

async def get_text_from_url(url: str) -> str:
    # Create an instance of AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        # Run the crawler on a URL
        result = await crawler.arun(url)
        return result.markdown

def split_text(text: str, split_type: str) -> List[BaseNode]:
    if split_type == "recursive":
        text_splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)
        nodes = text_splitter.get_nodes_from_documents([Document(text=text)])
    elif split_type == "semantic":
        embed_model = OpenAIEmbedding()
        text_splitter = SemanticSplitterNodeParser(
            buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
        )
        nodes = text_splitter.get_nodes_from_documents([Document(text=text)])
    else:
        raise ValueError(f"Invalid split type: {split_type}")
    return list(nodes)

def get_embedding(nodes: List[BaseNode]) -> List[BaseNode]:
    embed_model = OpenAIEmbedding()
    for node in nodes:
        node_embedding = embed_model.get_text_embedding(
            node.get_content(metadata_mode="all")
        )
        node.embedding = node_embedding
    return nodes
