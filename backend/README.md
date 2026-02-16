# PatentFlowIA Backend

Backend API for PatentFlowIA - A comprehensive patent analysis and management platform built with FastAPI, PostgreSQL, and pgvector for semantic search capabilities.

## Features

- **Modern FastAPI Architecture**: Async/await support with type hints
- **PostgreSQL with pgvector**: Semantic search using vector embeddings
- **JWT Authentication**: Secure user authentication and authorization
- **Async Task Processing**: Background job processing with Celery and Redis
- **Modular Design**: Clean separation of concerns (routers, services, models, schemas)
- **Docker Support**: Full containerization with Docker Compose
- **Database Migrations**: Alembic for version-controlled schema changes
- **Security Hardened**: Input validation, error handling, CORS, security headers
- **Advanced Search**: Top 5 similarity search with pgvector's `<=>` operator
- **Vertex AI / SentenceTransformers**: Dual embedding strategy with fallback
- **Espacenet Integration**: Patent scraper with Redis caching

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database connection and session management
│   ├── dependencies.py         # FastAPI dependencies (auth, db)
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── project.py
│   │   └── patent.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── patent.py
│   │   └── espacenet.py       # NEW: Espacenet schemas
│   ├── routers/                # API endpoints
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── projects.py
│   │   └── patents.py         # Enhanced with new search endpoints
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── patent_service.py
│   │   ├── vector_service.py  # Enhanced with top 5 search
│   │   ├── embedding_service.py   # NEW: Vertex AI + SentenceTransformers
│   │   ├── cache_service.py   # NEW: Redis caching
│   │   ├── patent_provider.py # NEW: Espacenet scraper
│   │   └── celery_tasks.py
│   ├── middleware/             # Custom middleware
│   │   ├── error_handler.py
│   │   └── security.py
│   └── utils/                  # Utilities
│       ├── security.py
│       └── validators.py
├── alembic/                    # Database migrations
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Poetry configuration
├── Dockerfile                 # Docker image definition
└── alembic.ini               # Alembic configuration
```

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- PostgreSQL 14+ (if running without Docker)
- Redis (if running without Docker)
- Optional: Google Cloud project for Vertex AI

## Quick Start with Docker

1. **Clone the repository**
   ```bash
   cd "c:\Users\sash\OneDrive - IPSA\Bureau\13.02.2026\patentflow ai2"
   ```

2. **Configure environment**
   ```bash
   cd backend
   copy .env.example .env
   # Edit .env if needed (defaults work for Docker setup)
   ```

3. **Start all services**
   ```bash
   cd ..
   docker compose up --build
   ```

   This will start:
   - PostgreSQL with pgvector extension (port 5432)
   - Redis (port 6379)
   - FastAPI backend (port 8000)
   - Celery worker

4. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc
   - Health check: http://localhost:8000/health

## Manual Installation (Without Docker)

1. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   copy .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Start Celery worker (in another terminal)**
   ```bash
   celery -A app.services.celery_tasks worker --loglevel=info
   ```

## NEW: Advanced Search Features

### Embedding Service

The backend now supports two embedding strategies:

1. **SentenceTransformers** (default, local)
   - Model: `all-MiniLM-L6-v2` (384 dimensions)
   - No external API required
   - Fast and free

2. **Vertex AI** (optional, cloud)
   - Model: `textembedding-gecko@003`
   - Requires Google Cloud project
   - Higher quality embeddings

Configure in `.env`:
```env
EMBEDDING_PROVIDER=sentence_transformers  # or "vertex_ai"
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# For Vertex AI (optional)
VERTEX_AI_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Top 5 Search

Optimized endpoint using pgvector's `<=>` operator for fast cosine similarity:

```bash
POST /api/patents/search/top5
{
  "query_text": "battery technology innovation",
  "similarity_threshold": 0.5
}
```

Returns exactly the 5 most similar patents.

### Espacenet Integration

Fetch patent metadata from Espacenet with Redis caching:

```bash
# Fetch metadata
GET /api/patents/espacenet/EP1234567

# Import into project
POST /api/patents/import/espacenet?patent_number=EP1234567&project_id={uuid}
```

Features:
- Automatic Redis caching (7-day TTL)
- Mock data for demo (replace with real API)
- Bright Data proxy support

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT tokens
- `POST /api/auth/refresh` - Refresh access token

### Users
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update current user profile

### Projects
- `POST /api/projects` - Create new project
- `GET /api/projects` - List all projects
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Patents
- `POST /api/patents` - Create new patent
- `GET /api/patents/{id}` - Get patent details
- `PUT /api/patents/{id}` - Update patent
- `DELETE /api/patents/{id}` - Delete patent
- `POST /api/patents/search` - Semantic search for similar patents
- **NEW** `POST /api/patents/search/top5` - Get top 5 similar patents
- **NEW** `GET /api/patents/espacenet/{patent_number}` - Fetch from Espacenet
- **NEW** `POST /api/patents/import/espacenet` - Import patent from Espacenet

### Health
- `GET /health` - Health check endpoint

## Configuration

Key environment variables (see `.env.example`):

### Database & Redis
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Security
- `SECRET_KEY` - JWT secret key
- `CORS_ORIGINS` - Allowed CORS origins

### Embeddings
- `EMBEDDING_PROVIDER` - "sentence_transformers" or "vertex_ai"
- `EMBEDDING_MODEL` - Model name
- `EMBEDDING_DIMENSION` - Vector dimension (384 or 768)

### Vertex AI (optional)
- `VERTEX_AI_PROJECT_ID` - GCP project ID
- `VERTEX_AI_LOCATION` - Region (e.g., "us-central1")
- `GOOGLE_APPLICATION_CREDENTIALS` - Service account JSON path

### Espacenet
- `ESPACENET_API_URL` - API endpoint
- `BRIGHT_DATA_PROXY` - Proxy configuration
- `REDIS_CACHE_TTL` - Cache duration (seconds)

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Vector Search Technical Details

### pgvector Cosine Distance

The `<=>` operator in pgvector computes cosine distance efficiently:

```sql
SELECT *, (1 - (embedding <=> query_vector)) AS similarity
FROM patents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> query_vector
LIMIT 5
```

- Distance range: [0, 2]
- Similarity: `1 - distance`
- IVFFlat index for performance

### Embedding Pipeline

1. User creates/updates patent
2. Celery task generates embedding asynchronously
3. Embedding stored in PostgreSQL with IVFFlat index
4. Search uses `<=>` for fast similarity queries

## Security Features

- **Password Hashing**: Bcrypt with automatic salt
- **JWT Tokens**: Secure authentication with access/refresh tokens
- **Input Validation**: Strict Pydantic validation with custom validators
- **Error Handling**: Global exception handler prevents information leakage
- **CORS**: Configurable cross-origin resource sharing
- **Security Headers**: X-Frame-Options, CSP, HSTS, etc.
- **Redis Cache**: TTL-based expiration for cached data

## Development

```bash
# Run tests
pytest

# Code formatting
black app/

# Linting
ruff app/
```

## Production Deployment

1. Update `.env` with production values
2. Set `ENVIRONMENT=prod`
3. Use a strong `SECRET_KEY`
4. Configure proper CORS origins
5. For Vertex AI: setup service account credentials
6. Use HTTPS reverse proxy (nginx, Traefik)
7. Enable database backups
8. Monitor with logging/metrics services
9. Configure Redis persistence
10. Scale Celery workers as needed

## Troubleshooting

**Database connection issues:**
- Ensure PostgreSQL is running and accessible
- Check DATABASE_URL format
- Verify pgvector extension is installed

**Celery tasks not running:**
- Ensure Redis is running
- Check CELERY_BROKER_URL
- Verify celery worker is started

**Embedding generation fails:**
- Check EMBEDDING_PROVIDER setting
- For Vertex AI: verify credentials and project ID
- For SentenceTransformers: ensure model is downloaded

**Espacenet scraper issues:**
- Check Redis connection
- Verify ESPACENET_API_URL
- Review cache keys in Redis

## License

Proprietary - PatentFlowIA Team

## Support

For issues and questions, please contact the development team.
