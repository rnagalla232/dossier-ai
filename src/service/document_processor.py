"""
Document Processor Service
Handles the full processing pipeline for uploaded documents:
1. Summarize document content using LLM
2. Categorize document (match to existing or create new category)
3. Update document with summary and category assignment
"""

import os
import json
from typing import Dict, Any, Optional, List
from bson import ObjectId
from openai import OpenAI
from src.helper.util import get_text_from_url
from src.service.document_service import DocumentService
from src.service.category_service import CategoryService
from src.model.resource import Document, CategoryCreate, ProcessingStatus


class DocumentProcessor:
    """Process documents with LLM-based summarization and categorization"""
    
    def __init__(self):
        """Initialize the document processor with LLM and service dependencies."""
        self.client = OpenAI(
            api_key=os.environ["SNOWFLAKE_API_KEY"],
            base_url="https://RQNIACH-ZF07937.snowflakecomputing.com/api/v2/cortex/v1"
        )
        self.model_name = "llama3.1-70b"
        self.document_service = DocumentService()
        self.category_service = CategoryService()
    
    async def generate_summary(self, url: str, content: str) -> str:
        """
        Generate a summary of the document content using LLM.
        
        Args:
            url: The document URL
            content: The text content to summarize
            
        Returns:
            Summary text
        """
        prompt = f"""
        Please provide a comprehensive summary of the following web content from {url}:
        
        First 4000 characters of Content:
        {content[:4000]} 
        
        Please create a short summary of the content in under 150 words. Include:
        1. A brief overview of the main topic
        2. Key points and important information
        3. Any notable conclusions or recommendations
        Do not include any additional information or commentary. Just the summary and nothing else, don't say here's the summary or anything like that.
        
        Short Summary:
        """
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert content summarizer. Provide clear, concise, and informative summaries."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=2000,
            temperature=0.2
        )
        
        return response.choices[0].message.content
    
    async def categorize_document(
        self, 
        user_id: str, 
        url: str, 
        summary: str, 
        existing_categories: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Use LLM to determine the best category for a document.
        
        Args:
            user_id: User ID
            url: Document URL
            summary: Document summary
            existing_categories: List of existing categories with their names and descriptions
            
        Returns:
            Dictionary with categorization decision:
            {
                "action": "use_existing" or "create_new",
                "category_name": str,
                "category_description": str (only for create_new)
            }
        """
        if not existing_categories:
            # No categories exist, ask LLM to suggest a new one
            prompt = f"""
            A user has uploaded a document from: {url}
            
            Document Summary:
            {summary}
            
            The user currently has no categories. Please suggest an appropriate category name and description for this document. The category name should be broad and should be a single word or phrase.
            Ex. category names: "crypto", "genai", "celebs", "new tech", "home decor", "news"
            
            Respond in JSON format:
            {{
                "action": "create_new",
                "category_name": "suggested category name (concise, 1-3 words)",
                "category_description": "brief description of what documents this category contains"
            }}
            """
        else:
            # Format existing categories for the prompt
            categories_text = "\n".join([
                f"- {cat['name']}: {cat['description']}" 
                for cat in existing_categories
            ])
            
            prompt = f"""
            A user has uploaded a document from: {url}
            
            Document Summary:
            {summary}
            
            The user has the following existing categories:
            {categories_text}
            
            Determine if this document fits into one of the existing categories, or if a new category should be created.
            
            If it fits into an existing category, respond with:
            {{
                "action": "use_existing",
                "category_name": "exact name of the existing category"
            }}
            
            If a new category is needed, respond with:
            {{
                "action": "create_new",
                "category_name": "suggested new category name (concise, 2-4 words)",
                "category_description": "brief description of what documents this category contains"
            }}
            If creating a new category, the category name should be broad and should be a single word or phrase.
            Ex. category names: "crypto", "genai", "celebs", "new tech", "home decor", "news"
            Respond ONLY with valid JSON, no additional text.
            """
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert document organizer. Analyze documents and categorize them appropriately. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=500,
            temperature=0.1
        )
        
        # Parse the LLM response
        response_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Sometimes LLM adds markdown code blocks, so strip those
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # Fallback: create a generic category if parsing fails
            return {
                "action": "create_new",
                "category_name": "Uncategorized",
                "category_description": "Documents that couldn't be automatically categorized"
            }
    
    async def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline.
        
        Args:
            document_id: Document ID to process
            user_id: User ID who owns the document
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Get the document
            document = self.document_service.get_document_by_id(document_id)
            if not document:
                return {
                    "success": False,
                    "message": f"Document {document_id} not found"
                }
            
            # Verify ownership
            if document.user_id != user_id:
                return {
                    "success": False,
                    "message": "Document does not belong to user"
                }
            
            # Step 1: Fetch content from URL
            content = await get_text_from_url(document.url)
            if not content or not content.strip():
                return {
                    "success": False,
                    "message": "No content found at the provided URL"
                }
            
            # Step 2: Generate summary
            summary = await self.generate_summary(document.url, content)
            
            # Update document with summary
            self.document_service.update_document_summary(document_id, summary)
            
            # Step 3: Get existing categories for the user
            categories = self.category_service.get_all_categories(user_id)
            existing_categories = [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description or ""
                }
                for cat in categories
            ]
            
            # Step 4: Categorize the document
            categorization = await self.categorize_document(
                user_id=user_id,
                url=document.url,
                summary=summary,
                existing_categories=existing_categories
            )
            
            # Step 5: Apply categorization
            category_id = None
            category_name = categorization.get("category_name")
            
            if categorization.get("action") == "use_existing":
                # Find the existing category by name
                existing_cat = next(
                    (cat for cat in categories if cat.name == category_name),
                    None
                )
                if existing_cat:
                    category_id = existing_cat.id
                    # Add document to this category
                    self.category_service.add_documents_to_category(
                        category_id=category_id,
                        document_ids=[document_id],
                        user_id=user_id
                    )
            elif categorization.get("action") == "create_new":
                # Create a new category
                new_category = self.category_service.create_category(
                    CategoryCreate(
                        user_id=user_id,
                        name=category_name,
                        description=categorization.get("category_description", "")
                    )
                )
                category_id = new_category.id
                
                # Add document to the new category
                self.category_service.add_documents_to_category(
                    category_id=category_id,
                    document_ids=[document_id],
                    user_id=user_id
                )
            
            return {
                "success": True,
                "document_id": document_id,
                "summary": summary,
                "categorization": categorization,
                "category_id": category_id,
                "content_length": len(content)
            }
            
        except Exception as e:
            import traceback
            print(f"Error processing document {document_id}:")
            print(traceback.format_exc())
            return {
                "success": False,
                "message": f"Error processing document: {str(e)}"
            }

