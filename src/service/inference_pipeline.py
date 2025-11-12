import asyncio
from typing import Dict, Any
from openai import OpenAI
import os
from src.model.resource import WebResource
from src.helper.util import get_text_from_url
from src.service.retrieval_pipeline import RetrievalPipelineService

class InferencePipelineService:
    def __init__(self, collection_name: str = "web_embeddings"):
        """Initialize the inference pipeline with LLM and retrieval capabilities."""
        self.client = OpenAI(
            api_key=os.environ["SNOWFLAKE_API_KEY"],
            base_url="https://RQNIACH-ZF07937.snowflakecomputing.com/api/v2/cortex/v1"
        )
        self.model_name = "llama3.1-70b"
        self.provider = "snowflake"
        self.retrieval_service = RetrievalPipelineService(collection_name=collection_name)
    
    async def get_summary(self, resource: WebResource) -> Dict[str, Any]:
        """
        Generate a summary of the web resource content.
        
        Args:
            resource: WebResource object containing the URL to summarize
            
        Returns:
            Dictionary with summary results
        """
        try:
            # Fetch content from URL
            # text_content = await get_text_from_url(url=resource.web_url)
            text_content = resource.page_content
            if not text_content or not text_content.strip():
                yield "Error: No content found at the provided URL"
                return
            if resource.isSummary:
                prompt =  f"""
                    Please provide a comprehensive summary of the following web content:
                    
                    First 4000 characters of Content:
                    {text_content[:4000]} 
                    
                    Please create a short summary of the content in under 150 words. Include:
                    1. A brief overview of the main topic
                    2. Key points and important information
                    3. Any notable conclusions or recommendations
                    
                    Short Summary:
                 """
                content = "You are an expert content short summarizer. Provide clear, concise, and informative summaries. Answer should be embedded in html tags."
            else:
                prompt =  f""" {text_content} """
                content = "You are an expert. Answer the question asked by the user elaborately. Answer should be embedded in html tags."
                print("content: ", content)
            
            
            # Call OpenAI API for summarization
            response = self.client.chat.completions.create(
                model="llama3.1-70b",
                messages=[
                    {"role": "system", "content": content},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=2000,
                temperature=0.3,
                stream=True
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                # if hasattr(chunk.choices[0].delta, "reasoning_content"):
                #     continue
                if content is not None:
                    print(content, end="", flush=True)
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    yield chunk.choices[0].delta.content
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            yield f"Error generating summary: {str(e)}"
            return
    
    # def query_llm(self, query_resource: QueryResource) -> Dict[str, Any]:
    #     """
    #     Query the LLM with context from the vector store.
        
    #     Args:
    #         query_resource: QueryResource object containing query and URL
            
    #     Returns:
    #         Dictionary with LLM response and context
    #     """
    #     try:
    #         # Get relevant context from vector store
    #         retrieval_result = self.retrieval_service.get_similar_nodes(
    #             query=query_resource.query,
    #             top_k=query_resource.top_k
    #         )
            
    #         if not retrieval_result["success"]:
    #             return {
    #                 "success": False,
    #                 "message": f"Error retrieving context: {retrieval_result['message']}",
    #                 "query": query_resource.query
    #             }
            
    #         # Extract relevant text from retrieved nodes
    #         context_texts = []
    #         for result in retrieval_result["results"]:
    #             context_texts.append(result["text"])
            
    #         # Combine context with query
    #         context = "\n\n".join(context_texts)
            
    #         # Create prompt with context
    #         prompt = f"""
    #         Based on the following context from {query_resource.web_url}, please answer the question.
            
    #         Context:
    #         {context}
            
    #         Question: {query_resource.query}
            
    #         Please provide a comprehensive answer based on the context provided. If the context doesn't contain enough information to answer the question, please state that clearly.
            
    #         Answer:
    #         """
            
    #         # Call OpenAI API with context
    #         response = self.client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context. Be accurate and cite relevant information from the context."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             max_tokens=1500,
    #             temperature=0.2
    #         )
            
    #         answer = response.choices[0].message.content
            
    #         return {
    #             "success": True,
    #             "answer": answer,
    #             "query": query_resource.query,
    #             "url": query_resource.web_url,
    #             "user_id": query_resource.user_id,
    #             "context_sources": len(retrieval_result["results"]),
    #             "context_preview": context[:500] + "..." if len(context) > 500 else context
    #         }
            
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "message": f"Error querying LLM: {str(e)}",
    #             "query": query_resource.query
    #         }
    
    # def get_conversation_summary(self, chat_history: list) -> Dict[str, Any]:
    #     """
    #     Generate a summary of the conversation history.
        
    #     Args:
    #         chat_history: List of chat messages
            
    #     Returns:
    #         Dictionary with conversation summary
    #     """
    #     try:
    #         # Format chat history
    #         formatted_history = ""
    #         for message in chat_history:
    #             role = message.get("role", "user")
    #             content = message.get("content", "")
    #             formatted_history += f"{role.capitalize()}: {content}\n"
            
    #         prompt = f"""
    #         Please provide a summary of the following conversation:
            
    #         {formatted_history}
            
    #         Please include:
    #         1. Main topics discussed
    #         2. Key decisions or conclusions
    #         3. Important information shared
    #         4. Any action items or next steps
            
    #         Conversation Summary:
    #         """
            
    #         response = self.client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {"role": "system", "content": "You are an expert at summarizing conversations. Provide clear, structured summaries."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             max_tokens=800,
    #             temperature=0.3
    #         )
            
    #         summary = response.choices[0].message.content
            
    #         return {
    #             "success": True,
    #             "conversation_summary": summary,
    #             "message_count": len(chat_history)
    #         }
            
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "message": f"Error generating conversation summary: {str(e)}"
    #         }
