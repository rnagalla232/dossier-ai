"""
Inference pipeline service for LLM-based summarization and Q&A.
Handles streaming and non-streaming responses from Snowflake Cortex.
"""
import logging
from typing import Dict, Any, AsyncGenerator
from openai import OpenAI

from src.config import settings
from src.model.resource import WebResource
from src.service.retrieval_pipeline import RetrievalPipelineService


logger = logging.getLogger(__name__)


class InferencePipelineService:
    """Service for LLM inference operations using Snowflake Cortex."""
    
    def __init__(self, collection_name: str = "web_embeddings"):
        """
        Initialize the inference pipeline with LLM and retrieval capabilities.
        
        Args:
            collection_name: Name of the vector store collection for retrieval
        """
        self.client = OpenAI(
            api_key=settings.snowflake_api_key,
            base_url=settings.snowflake_base_url
        )
        self.model_name = settings.snowflake_model
        self.provider = "snowflake"
        self.retrieval_service = RetrievalPipelineService(
            collection_name=collection_name
        )
    
    async def get_summary(
        self,
        resource: WebResource
    ) -> AsyncGenerator[str, None]:
        """
        Generate a summary of the web resource content with streaming.
        
        Args:
            resource: WebResource object containing the content to summarize
            
        Yields:
            Summary chunks as they are generated
            
        Raises:
            Exception: If summarization fails
        """
        try:
            # Get content from resource
            text_content = resource.page_content
            
            # Validate content
            if not text_content or not text_content.strip():
                yield "Error: No content found at the provided URL"
                return
            
            # Build prompt based on request type
            if resource.isSummary:
                prompt = self._build_summary_prompt(text_content)
                system_message = (
                    "You are an expert content summarizer. Provide clear, "
                    "concise, and informative summaries. Format your answer "
                    "using HTML tags for better readability."
                )
            else:
                prompt = text_content
                system_message = (
                    "You are an expert assistant. Answer the user's question "
                    "elaborately and comprehensively. Format your answer using "
                    "HTML tags for better readability."
                )
            
            # Call LLM API for streaming response
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=settings.max_completion_tokens,
                temperature=settings.temperature,
                stream=True
            )
            
            # Stream response chunks
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content is not None:
                    logger.debug(f"Streaming chunk: {content}")
                    yield content
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}", exc_info=True)
            yield f"Error generating summary: {str(e)}"
            return
    
    def _build_summary_prompt(self, text_content: str) -> str:
        """
        Build a prompt for summarization.
        
        Args:
            text_content: Text content to summarize
            
        Returns:
            Formatted prompt string
        """
        # Truncate content to avoid token limits
        content_preview = text_content[:4000]
        
        prompt = f"""
Please provide a comprehensive summary of the following web content:

First 4000 characters of Content:
{content_preview}

Please create a concise summary in under 150 words that includes:
1. A brief overview of the main topic
2. Key points and important information
3. Any notable conclusions or recommendations

Summary:
"""
        return prompt.strip()
