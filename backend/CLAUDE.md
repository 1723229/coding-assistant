# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based web platform that provides a web interface for Claude Code. It enables multi-turn conversations with Claude SDK, session management, workspace isolation, GitHub integration, and project/module/version management. The backend serves as a bridge between a web frontend and the Claude Agent SDK.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Claude Agent SDK (if needed)
pip install git+https://github.com/anthropics/claude-agent-sdk-python.git
```

### Configuration
Copy `app/config/config.example.yaml` to `app/config/config.yaml` and configure:
- Database credentials (MySQL)
- Claude API key and base URL
- Server settings (host, port, CORS)
- Workspace base path
- GitHub token (optional)

### Running the Application
```bash
# Development mode (with auto-reload)
python app/main.py

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# With custom host/port
python app/main.py --host 127.0.0.1 --port 8080 --reload
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_claude_service.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Docker
```bash
# Build image
docker build -t claude-workspace:latest .

# Run container
docker run -p 8000:8000 -v $(pwd)/workspaces:/app/workspaces claude-workspace:latest
```

## Architecture

### Layered Architecture
The application follows a clean layered architecture pattern:

1. **API Layer** (`app/api/`) - FastAPI routers handling HTTP/SSE requests
2. **Service Layer** (`app/service/`) - Business logic and orchestration
3. **Core Layer** (`app/core/`) - Core functionality (Claude SDK, GitHub, Docker integrations)
4. **Repository Layer** (`app/db/repository/`) - Database access abstraction
5. **Models & Schemas** (`app/db/models/`, `app/db/schemas/`) - Data structures

### Sandbox Executor Architecture

The application uses a dual-execution model:

- **SessionClaudeManager** (`app/core/claude_service.py:408`) - Legacy direct execution, manages Claude SDK instances for simple chat sessions
- **SandboxExecutor** (`app/core/executor.py`) - Production execution mode that runs all Claude operations in isolated Docker containers

Each sandbox container:
- Runs the `coding-assistant-executor` Docker image (built from `backend/executor/Dockerfile`)
- Has its own isolated workspace mounted as a volume
- Exposes two ports: API port (10001-10100 range) and Code service port (20001-20100 range)
- Has resource limits (4GB memory, 2 CPUs by default)
- Communicates back to host via `host.docker.internal` (Mac/Windows) or host IP (Linux)

The executor handles:
- Container lifecycle (create, start, stop, restart, health checks)
- Port allocation from configured ranges
- Workspace volume mounting
- Session timeout cleanup (30 minutes default)
- Streaming and non-streaming chat requests proxied to containers

### Project/Module/Version Hierarchy

The application manages a three-level hierarchy:

1. **Projects** (`app/db/models/project.py`) - Top-level container with codebase URL, GitHub token, branch
2. **Modules** (`app/db/models/module.py`) - Two types:
   - **NODE** - Organizational nodes for tree structure, URL shared with children
   - **POINT** - Leaf nodes that create actual workspaces, sessions, and containers
3. **Versions** (`app/db/models/version.py`) - Track commits for each module's code changes

POINT module creation flow (`app/service/module_service.py:169`):
1. Generate session_id and workspace_path
2. Clone GitHub repository to workspace
3. Create feature branch (`{branch}-{session_id}`)
4. Generate technical spec document using Claude
5. Generate code from spec and create initial commit
6. Create version record
7. Create sandbox container
8. Insert menu entry into `sys_module` table (direct MySQL access)

### Dual Database Access Pattern

Most data access uses SQLAlchemy repositories, but some services use direct MySQL connections:
- `ModuleService` uses `MySQLUtil` for `sys_module` table operations (`app/service/module_service.py:50`)
- This table exists in a separate "framework" database for UI menu integration
- Always use `MySQLUtil` for `sys_module`, repositories for all other tables

### Multi-Turn Conversation System

The application maintains conversation context across multiple exchanges using `ClaudeSDKClient` with session IDs:

- **SessionClaudeManager** (`app/core/claude_service.py:408`) - Global manager that maintains Claude service instances per session, handles session cleanup, and connection reuse
- **ClaudeService** (`app/core/claude_service.py:107`) - Wraps Claude Agent SDK for single session operations, manages client lifecycle, and provides streaming chat
- **Session Continuity** - Each chat request with the same `session_id` maintains conversation history via `client.query(prompt, session_id=session_id)` at `app/core/claude_service.py:245`

### Streaming Architecture

The application uses Server-Sent Events (SSE) for streaming Claude responses:

- **chat_stream_generator** (`app/api/chat_router.py:104`) - Async generator that yields SSE-formatted messages
- **Message Types** (`app/core/claude_service.py:41`) - Structured message types: TEXT, TEXT_DELTA, TOOL_USE, TOOL_RESULT, THINKING, ERROR, etc.
- **SessionManager** (`app/api/chat_router.py:46`) - Tracks active streaming sessions and handles interruptions

### Database Design

Uses SQLAlchemy async with MySQL:
- **BaseRepository** (`app/db/repository/base_repository.py`) - Generic repository pattern with common CRUD operations
- **Models** - Session, Message, Repository, GitHubToken with standard audit fields (create_time, update_time, create_by, update_by)
- **async_with_session** - Context manager for automatic transaction management

### Configuration System

YAML-based configuration (`app/config/config.yaml`) with class-based access:
- `DatabaseConfig` - Connection pooling, timeouts
- `ServerConfig` - Host, port, CORS, debug settings, preview_ip for container URLs
- `WorkspaceConfig` - Base path for isolated workspaces
- `GitHubConfig` - Token and default repo
- `DockerConfig` - Legacy container settings (not actively used)
- `ExecutorConfig` - **Primary configuration** for sandbox containers:
  - Docker image name (`coding-assistant-executor:latest`)
  - Port ranges for API (10001-10100) and Code service (20001-20100)
  - Timeouts (request: 300s, stream: 600s, health check: 30s)
  - Resource limits (memory: 4g, CPU: 2 cores)
  - Claude API credentials passed to containers (key, base_url, model)
  - Docker host address for container-to-host communication

Configuration classes are immutable and loaded once at startup from `app/config/settings.py`.

## Key Implementation Details

### Adding New API Endpoints

1. Create router in `app/api/` (e.g., `my_router.py`)
2. Create service in `app/service/` for business logic
3. Create repository in `app/db/repository/` if database access needed
4. Register router in `app/main.py` with `app.include_router()`

### Working with Claude SDK

The `ClaudeService` class provides two main methods:
- `chat_stream()` - Async generator for streaming responses (use for real-time UI)
- `chat()` - Non-streaming that collects all responses (use for batch operations)

Always use `session_claude_manager.get_service()` to get a service instance - never instantiate `ClaudeService` directly.

### Database Operations

All repositories extend `BaseRepository` which provides:
- `get_by_id()`, `get_multi()`, `count()` - Read operations
- `create()`, `update()`, `delete()` - Write operations
- Automatic filter and ordering support

Use the `@async_with_session` decorator or context manager for transaction handling.

### Error Handling

Global exception handlers are registered in `app/utils/exceptions/exception_handlers.py`. Custom exceptions inherit from `BaseAPIException` in `app/utils/exceptions/base_exceptions.py`.

All API responses follow the standard format from `app/utils/model/response_model.py`:
- `BaseResponse.success()` / `BaseResponse.error()` for single items
- `ListResponse.success()` for collections

### Session Cleanup

`SessionClaudeManager` runs a background cleanup task (every 5 minutes) that closes sessions inactive for longer than `ClaudeConfig.SESSION_TIMEOUT` (default 30 minutes). The cleanup task starts during app startup via the `lifespan` context manager in `app/main.py:50`.

### MCP Server Integration

The application integrates Puppeteer MCP server for browser automation:
- Configured in `ClaudeService._create_options()` at `app/core/claude_service.py:168`
- Available tools: `mcp__puppeteer__puppeteer_navigate`, `puppeteer_screenshot`, `puppeteer_click`, `puppeteer_fill`, etc.
- Defined in `PUPPETEER_TOOLS` list at `app/core/claude_service.py:76`

## Important Patterns

### Workspace Isolation
Each session has its own workspace directory under `WorkspaceConfig.BASE_PATH`. Claude operates within this directory (set as `cwd` in `ClaudeAgentOptions`).

### Permission Modes
Claude SDK permission mode defaults to `acceptEdits` but can be configured:
- `acceptEdits` - User must approve file edits
- `bypassPermissions` - Auto-approve all operations
- Set via `ClaudeConfig.PERMISSION_MODE` in config.yaml

### Logging
Centralized logging configured in `app/config/logging_config.py`. Use `@log_print` decorator for automatic request/response logging in service methods.

### Async Patterns
- All database operations are async
- Use `async with async_engine.begin()` for transactions
- Connection pooling configured in `app/db/base.py` (NullPool for async to prevent event loop issues)

## Environment Variables

The application primarily uses `config.yaml` but also respects:
- `ANTHROPIC_API_KEY` - Set automatically from config via `ClaudeConfig.setup_environment()`
- `ANTHROPIC_BASE_URL` - Set automatically from config
- `GITHUB_TOKEN` - Falls back to config if not in environment

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

API endpoints are organized by prefix:
- `/api/code/sessions` - Session management
- `/api/code/chat` - Chat and streaming
- `/api/code/github` - GitHub integration
- `/api/code/workspace` - Workspace operations
