# Web Content Intelligence API

A FastAPI-based backend service for intelligent web content crawling, indexing, and retrieval with AI-powered summarization using Snowflake Cortex and OpenAI.

## 🚀 Features

- **Document Management**: Full CRUD REST APIs for managing web documents with MongoDB
- **Web Crawling**: Extract content from web pages using Crawl4AI and Playwright
- **Vector Storage**: Store and query embeddings using Qdrant vector database
- **AI Summarization**: Generate intelligent summaries using Snowflake Cortex (Llama 3.1 70B)
- **Semantic Search**: Retrieve relevant content using OpenAI embeddings
- **RESTful API**: Fast and async API endpoints with FastAPI

## 📋 Prerequisites

- Python 3.13+
- MongoDB (running locally on port 27017)
- Qdrant (running locally on port 6333)
- Snowflake account with Cortex API access
- OpenAI API key
- Docker (optional, for containerized deployment)

## 🛠️ Installation & Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd backend
```

### 2. Create and activate virtual environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Chromium

For corporate environments with SSL inspection:

```bash
NODE_TLS_REJECT_UNAUTHORIZED=0 python -m playwright install chromium
```

Or simply run:

```bash
bash run.sh
```

### 5. Set up environment variables

Copy the example environment file and fill in your credentials:

```bash
cp env.example .env
```

Edit `.env` with your actual API keys and MongoDB connection:

```env
SNOWFLAKE_API_KEY=your_snowflake_api_key
OPENAI_API_KEY=your_openai_api_key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=document_db
```

### 6. Start MongoDB

Using Docker:

```bash
bash iaac/setup-mongo-docker.sh
```

Or manually:

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 7. Start Qdrant Vector Database

Using Docker:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Or use the setup script if available:

```bash
bash iaac/setup-qdrant-docker.sh
```

### 8. Run the server

```bash
uvicorn src.api.route:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## 🐳 Docker Deployment

### Build and run with Docker

```bash
docker build -t web-intelligence-api .
docker run -p 8000:8000 -e SNOWFLAKE_API_KEY=your_key -e OPENAI_API_KEY=your_key web-intelligence-api
```

### Using Docker Compose

```bash
docker-compose up -d
```

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔌 API Endpoints

### Document Management APIs

Complete CRUD operations for managing web documents. See [detailed documentation](docs/DOCUMENT_API.md).

#### Create Document

```http
POST /documents
Content-Type: application/json

{
  "user_id": "user123",
  "url": "https://example.com",
  "title": "Example Document",
  "dom": "<html>...</html>"
}
```

#### Get All Documents

```http
GET /documents?user_id=user123&skip=0&limit=100
```

#### Get Specific Document

```http
GET /documents/{document_id}
```

#### Update Document

```http
PUT /documents/{document_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description"
}
```

#### Delete Document

```http
DELETE /documents/{document_id}
```

**📖 [View Complete Document API Documentation](docs/DOCUMENT_API.md)**

**🧪 [Run API Test Examples](examples/test_document_api.py)**

---

### Health Check

```http
GET /
```

Returns server status.

### Generate Summary

```http
POST /summary
Content-Type: application/json

{
  "user_id": "your_user_id",
  "web_url": "https://example.com"
}
```

Generates an AI-powered summary of the web page content.

### Index Web Resource

```http
POST /index/webresource
Content-Type: application/json

{
  "user_id": "your_user_id",
  "web_url": "https://example.com"
}
```

Crawls and indexes the web page into the vector database.

### Query Vector Store

```http
POST /retrieve/query
Content-Type: application/json

{
  "query": "What is the main topic?"
}
```

Retrieves relevant content from the vector database based on semantic similarity.

## 📁 Project Structure

```
backend/
├── src/
│   ├── api/
│   │   └── route.py              # FastAPI routes
│   ├── service/
│   │   ├── document_service.py   # Document CRUD operations
│   │   ├── inference_pipeline.py  # LLM inference & summarization
│   │   ├── ingestion_pipeline.py  # Content ingestion & indexing
│   │   └── retrieval_pipeline.py  # Vector search & retrieval
│   ├── model/
│   │   └── resource.py           # Pydantic models
│   └── helper/
│       ├── mongodb.py            # MongoDB connection helper
│       └── util.py               # Utility functions
├── docs/
│   └── DOCUMENT_API.md           # Document API documentation
├── examples/
│   └── test_document_api.py      # API usage examples
├── iaac/                         # Infrastructure scripts
├── qdrant_storage/               # Vector DB storage (gitignored)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml            # Docker Compose setup
├── run.sh                        # Quick setup script
├── env.example                   # Environment variables template
└── README.md                     # This file
```

## 🔧 Development

### Debug Mode

Run with debug logging:

```bash
uvicorn src.api.route:app --reload --port 8000 --log-level debug
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.api.route:app",
                "--reload",
                "--port",
                "8000"
            ],
            "jinja": true,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

## 🛡️ Security Notes

### SSL Certificate Issues

If you're in a corporate environment with SSL inspection, you may need to disable SSL verification:

```bash
NODE_TLS_REJECT_UNAUTHORIZED=0
```

⚠️ **Warning**: Only use this in development. For production, obtain proper CA certificates from your IT department.

### API Keys

- Never commit API keys to version control
- Use environment variables or secret management services
- Rotate keys regularly
- Use `.env` files locally (already in `.gitignore`)

## 🧪 Testing

### Test Document APIs

Run the example test script:

```bash
# Make sure the server is running first
./run.sh

# In a new terminal, run the test script
python examples/test_document_api.py
```

### Run unit tests (when available):

```bash
pytest tests/
```

## 📊 Tech Stack

- **FastAPI** - Modern Python web framework
- **MongoDB** - NoSQL database for document storage
- **PyMongo** - MongoDB Python driver
- **Crawl4AI** - Intelligent web crawling
- **Playwright** - Headless browser automation
- **Qdrant** - Vector database for embeddings
- **LlamaIndex** - LLM orchestration framework
- **Snowflake Cortex** - LLM inference (Llama 3.1 70B)
- **OpenAI** - Text embeddings
- **Uvicorn** - ASGI server

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

[Your License Here]

## 👤 Author

[Your Name]

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find and kill the process using port 8000
lsof -ti:8000 | xargs kill -9
```

### MongoDB Connection Issues

Make sure MongoDB is running:

```bash
docker ps | grep mongodb
```

If not running, start it:

```bash
bash iaac/setup-mongo-docker.sh
```

### Qdrant Connection Issues

Make sure Qdrant is running:

```bash
docker ps | grep qdrant
```

### SSL Certificate Errors

Set environment variable:

```bash
export NODE_TLS_REJECT_UNAUTHORIZED=0
```

### Module Import Errors

Ensure you're in the project root and virtual environment is activated:

```bash
cd backend
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## 📞 Support

For issues and questions, please open an issue on GitHub.

