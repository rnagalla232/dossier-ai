"""
Tests for Document Processor Service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.service.document_processor import DocumentProcessor
from src.model.resource import Document, Category, ProcessingStatus
from datetime import datetime, timezone


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    with patch('src.service.document_processor.OpenAI') as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_document_service():
    """Mock DocumentService"""
    with patch('src.service.document_processor.DocumentService') as mock:
        service = Mock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_category_service():
    """Mock CategoryService"""
    with patch('src.service.document_processor.CategoryService') as mock:
        service = Mock()
        mock.return_value = service
        yield service


@pytest.fixture
def processor(mock_openai_client, mock_document_service, mock_category_service):
    """Create a DocumentProcessor instance with mocked dependencies"""
    return DocumentProcessor()


@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return Document(
        id="doc123",
        user_id="user123",
        url="https://example.com/article",
        title="Test Article",
        processing_status=ProcessingStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_categories():
    """Sample categories for testing"""
    return [
        Category(
            id="cat1",
            user_id="user123",
            name="Technology",
            description="Articles about technology and software",
            document_ids=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        Category(
            id="cat2",
            user_id="user123",
            name="Science",
            description="Scientific research and discoveries",
            document_ids=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    ]


class TestGenerateSummary:
    """Tests for generate_summary method"""
    
    @pytest.mark.asyncio
    async def test_generate_summary_success(self, processor, mock_openai_client):
        """Test successful summary generation"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test summary of the article."
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test
        url = "https://example.com/article"
        content = "This is a long article about technology. " * 100
        summary = await processor.generate_summary(url, content)
        
        # Assertions
        assert summary == "This is a test summary of the article."
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['model'] == "llama3.1-70b"
        assert call_args[1]['temperature'] == 0.2
    
    @pytest.mark.asyncio
    async def test_generate_summary_with_long_content(self, processor, mock_openai_client):
        """Test summary generation with content longer than 4000 chars"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summary of long content."
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test with very long content
        url = "https://example.com/long-article"
        content = "A" * 10000  # 10000 characters
        summary = await processor.generate_summary(url, content)
        
        # Assertions
        assert summary == "Summary of long content."
        # Verify that only first 4000 chars were sent in prompt
        call_args = mock_openai_client.chat.completions.create.call_args
        prompt = call_args[1]['messages'][1]['content']
        assert "A" * 4000 in prompt
        assert len(content[:4000]) == 4000


class TestCategorizeDocument:
    """Tests for categorize_document method"""
    
    @pytest.mark.asyncio
    async def test_categorize_with_no_existing_categories(self, processor, mock_openai_client):
        """Test categorization when user has no categories"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "action": "create_new",
            "category_name": "Technology",
            "category_description": "Articles about technology and software"
        }
        '''
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test
        result = await processor.categorize_document(
            user_id="user123",
            url="https://example.com/tech-article",
            summary="An article about Python programming",
            existing_categories=[]
        )
        
        # Assertions
        assert result["action"] == "create_new"
        assert result["category_name"] == "Technology"
        assert "category_description" in result
    
    @pytest.mark.asyncio
    async def test_categorize_with_existing_categories_use_existing(
        self, processor, mock_openai_client, sample_categories
    ):
        """Test categorization that matches an existing category"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "action": "use_existing",
            "category_name": "Technology"
        }
        '''
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test
        existing_cats = [
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in sample_categories
        ]
        result = await processor.categorize_document(
            user_id="user123",
            url="https://example.com/tech-article",
            summary="An article about Python programming",
            existing_categories=existing_cats
        )
        
        # Assertions
        assert result["action"] == "use_existing"
        assert result["category_name"] == "Technology"
    
    @pytest.mark.asyncio
    async def test_categorize_with_existing_categories_create_new(
        self, processor, mock_openai_client, sample_categories
    ):
        """Test categorization that requires a new category"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "action": "create_new",
            "category_name": "Philosophy",
            "category_description": "Philosophical discussions and theories"
        }
        '''
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test
        existing_cats = [
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in sample_categories
        ]
        result = await processor.categorize_document(
            user_id="user123",
            url="https://example.com/philosophy-article",
            summary="An article about existentialism",
            existing_categories=existing_cats
        )
        
        # Assertions
        assert result["action"] == "create_new"
        assert result["category_name"] == "Philosophy"
        assert "category_description" in result
    
    @pytest.mark.asyncio
    async def test_categorize_with_json_in_code_block(self, processor, mock_openai_client):
        """Test handling of JSON wrapped in markdown code blocks"""
        # Setup mock response with markdown code blocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
        {
            "action": "create_new",
            "category_name": "Health",
            "category_description": "Health and wellness articles"
        }
        ```'''
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test
        result = await processor.categorize_document(
            user_id="user123",
            url="https://example.com/health-article",
            summary="An article about nutrition",
            existing_categories=[]
        )
        
        # Assertions
        assert result["action"] == "create_new"
        assert result["category_name"] == "Health"
    
    @pytest.mark.asyncio
    async def test_categorize_with_invalid_json(self, processor, mock_openai_client):
        """Test fallback when LLM returns invalid JSON"""
        # Setup mock response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not valid JSON at all"
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test
        result = await processor.categorize_document(
            user_id="user123",
            url="https://example.com/article",
            summary="Some article",
            existing_categories=[]
        )
        
        # Assertions - should fallback to Uncategorized
        assert result["action"] == "create_new"
        assert result["category_name"] == "Uncategorized"


class TestProcessDocument:
    """Tests for the full document processing pipeline"""
    
    @pytest.mark.asyncio
    async def test_process_document_success_with_new_category(
        self, processor, mock_document_service, mock_category_service, 
        mock_openai_client, sample_document
    ):
        """Test successful document processing with new category creation"""
        # Setup mocks
        mock_document_service.get_document_by_id.return_value = sample_document
        mock_category_service.get_all_categories.return_value = []
        
        # Mock get_text_from_url
        with patch('src.service.document_processor.get_text_from_url') as mock_get_text:
            mock_get_text.return_value = "This is the article content about Python programming."
            
            # Mock LLM responses
            summary_response = Mock()
            summary_response.choices = [Mock()]
            summary_response.choices[0].message.content = "A summary about Python."
            
            categorization_response = Mock()
            categorization_response.choices = [Mock()]
            categorization_response.choices[0].message.content = '''
            {
                "action": "create_new",
                "category_name": "Programming",
                "category_description": "Programming articles and tutorials"
            }
            '''
            
            mock_openai_client.chat.completions.create.side_effect = [
                summary_response,
                categorization_response
            ]
            
            # Mock category creation
            new_category = Category(
                id="cat_new",
                user_id="user123",
                name="Programming",
                description="Programming articles and tutorials",
                document_ids=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            mock_category_service.create_category.return_value = new_category
            mock_category_service.add_documents_to_category.return_value = new_category
            
            # Test
            result = await processor.process_document(
                document_id="doc123",
                user_id="user123"
            )
            
            # Assertions
            assert result["success"] is True
            assert result["document_id"] == "doc123"
            assert "summary" in result
            assert result["categorization"]["action"] == "create_new"
            assert result["category_id"] == "cat_new"
            
            # Verify calls
            mock_document_service.update_document_summary.assert_called_once()
            mock_category_service.create_category.assert_called_once()
            mock_category_service.add_documents_to_category.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_success_with_existing_category(
        self, processor, mock_document_service, mock_category_service, 
        mock_openai_client, sample_document, sample_categories
    ):
        """Test successful document processing with existing category"""
        # Setup mocks
        mock_document_service.get_document_by_id.return_value = sample_document
        mock_category_service.get_all_categories.return_value = sample_categories
        
        # Mock get_text_from_url
        with patch('src.service.document_processor.get_text_from_url') as mock_get_text:
            mock_get_text.return_value = "This is an article about AI and machine learning."
            
            # Mock LLM responses
            summary_response = Mock()
            summary_response.choices = [Mock()]
            summary_response.choices[0].message.content = "A summary about AI."
            
            categorization_response = Mock()
            categorization_response.choices = [Mock()]
            categorization_response.choices[0].message.content = '''
            {
                "action": "use_existing",
                "category_name": "Technology"
            }
            '''
            
            mock_openai_client.chat.completions.create.side_effect = [
                summary_response,
                categorization_response
            ]
            
            mock_category_service.add_documents_to_category.return_value = sample_categories[0]
            
            # Test
            result = await processor.process_document(
                document_id="doc123",
                user_id="user123"
            )
            
            # Assertions
            assert result["success"] is True
            assert result["categorization"]["action"] == "use_existing"
            assert result["category_id"] == "cat1"
            
            # Verify category creation was NOT called
            mock_category_service.create_category.assert_not_called()
            # Verify document was added to existing category
            mock_category_service.add_documents_to_category.assert_called_once_with(
                category_id="cat1",
                document_ids=["doc123"],
                user_id="user123"
            )
    
    @pytest.mark.asyncio
    async def test_process_document_not_found(
        self, processor, mock_document_service
    ):
        """Test processing when document doesn't exist"""
        mock_document_service.get_document_by_id.return_value = None
        
        result = await processor.process_document(
            document_id="nonexistent",
            user_id="user123"
        )
        
        assert result["success"] is False
        assert "not found" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_process_document_wrong_user(
        self, processor, mock_document_service, sample_document
    ):
        """Test processing when document belongs to different user"""
        mock_document_service.get_document_by_id.return_value = sample_document
        
        result = await processor.process_document(
            document_id="doc123",
            user_id="wrong_user"
        )
        
        assert result["success"] is False
        assert "not belong" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_process_document_no_content(
        self, processor, mock_document_service, sample_document
    ):
        """Test processing when URL returns no content"""
        mock_document_service.get_document_by_id.return_value = sample_document
        
        with patch('src.service.document_processor.get_text_from_url') as mock_get_text:
            mock_get_text.return_value = ""
            
            result = await processor.process_document(
                document_id="doc123",
                user_id="user123"
            )
            
            assert result["success"] is False
            assert "no content" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_process_document_exception_handling(
        self, processor, mock_document_service, sample_document
    ):
        """Test exception handling during processing"""
        mock_document_service.get_document_by_id.return_value = sample_document
        
        with patch('src.service.document_processor.get_text_from_url') as mock_get_text:
            mock_get_text.side_effect = Exception("Network error")
            
            result = await processor.process_document(
                document_id="doc123",
                user_id="user123"
            )
            
            assert result["success"] is False
            assert "error" in result["message"].lower()

