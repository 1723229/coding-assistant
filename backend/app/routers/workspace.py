"""
Workspace file operations API.

Provides endpoints for file system operations within session workspaces.
"""

import os
import aiofiles
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_db
from app.db.schemas import FileInfo, FileContent, FileWriteRequest
from app.db.repository import SessionRepository
from app.config import get_settings

router = APIRouter()
settings = get_settings()

# Repository instance
session_repo = SessionRepository()


def get_safe_path(workspace_path: str, relative_path: str) -> Path:
    """Get safe absolute path within workspace.
    
    Prevents path traversal attacks by ensuring the resolved path
    is within the workspace directory.
    """
    workspace = Path(workspace_path).resolve()
    target = (workspace / relative_path).resolve()
    
    # Ensure path is within workspace
    if not str(target).startswith(str(workspace)):
        raise HTTPException(status_code=403, detail="Access denied: path outside workspace")
    
    return target


@router.get("/{session_id}/files", response_model=List[FileInfo])
async def list_files(
    session_id: str,
    path: str = Query(default="", description="Relative path within workspace"),
    db: AsyncSession = Depends(get_async_db)
) -> List[FileInfo]:
    """List files in workspace directory."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    # Ensure workspace_path is absolute
    workspace_path = Path(session.workspace_path).resolve()
    
    # Create workspace if it doesn't exist
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    target_path = get_safe_path(session.workspace_path, path)
    
    if not target_path.exists():
        return []
    
    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    files = []
    for item in sorted(target_path.iterdir()):
        # Skip hidden files and common ignore patterns
        if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules', '.git']:
            continue
            
        rel_path = str(item.relative_to(workspace_path))
        files.append(FileInfo(
            name=item.name,
            path=rel_path,
            is_directory=item.is_dir(),
            size=item.stat().st_size if item.is_file() else None,
        ))
    
    return files


@router.get("/{session_id}/files/content", response_model=FileContent)
async def get_file_content(
    session_id: str,
    path: str = Query(..., description="Relative path to file"),
    db: AsyncSession = Depends(get_async_db)
) -> FileContent:
    """Get file content."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    target_path = get_safe_path(session.workspace_path, path)
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not target_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    # Check file size (limit to 1MB)
    max_size = 1024 * 1024  # 1MB
    if target_path.stat().st_size > max_size:
        raise HTTPException(status_code=413, detail="File too large")
    
    try:
        async with aiofiles.open(target_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file cannot be read as text")
    
    return FileContent(path=path, content=content)


@router.put("/{session_id}/files/content", response_model=FileContent)
async def write_file_content(
    session_id: str,
    path: str = Query(..., description="Relative path to file"),
    data: FileWriteRequest = None,
    db: AsyncSession = Depends(get_async_db)
) -> FileContent:
    """Write file content."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    target_path = get_safe_path(session.workspace_path, path)
    
    # Create parent directories if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(target_path, mode='w', encoding='utf-8') as f:
        await f.write(data.content)
    
    return FileContent(path=path, content=data.content)


@router.delete("/{session_id}/files")
async def delete_file(
    session_id: str,
    path: str = Query(..., description="Relative path to file"),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a file or directory."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    target_path = get_safe_path(session.workspace_path, path)
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if target_path.is_dir():
        import shutil
        shutil.rmtree(target_path)
    else:
        target_path.unlink()
    
    return {"status": "deleted", "path": path}


@router.post("/{session_id}/files/mkdir", response_model=FileInfo)
async def create_directory(
    session_id: str,
    path: str = Query(..., description="Relative path for new directory"),
    db: AsyncSession = Depends(get_async_db)
) -> FileInfo:
    """Create a directory."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    target_path = get_safe_path(session.workspace_path, path)
    
    if target_path.exists():
        raise HTTPException(status_code=409, detail="Path already exists")
    
    target_path.mkdir(parents=True, exist_ok=True)
    
    return FileInfo(
        name=target_path.name,
        path=path,
        is_directory=True,
    )


@router.get("/{session_id}/files/tree")
async def get_file_tree(
    session_id: str,
    max_depth: int = Query(3, ge=1, le=10, description="Maximum depth to traverse"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get file tree structure for workspace."""
    session = await session_repo.get_session_by_id(session_id)
    
    if not session or not session.workspace_path:
        raise HTTPException(status_code=404, detail="Session or workspace not found")
    
    workspace_path = Path(session.workspace_path).resolve()
    
    if not workspace_path.exists():
        return {"name": workspace_path.name, "path": "", "children": []}
    
    def build_tree(path: Path, current_depth: int) -> dict:
        """Recursively build file tree."""
        rel_path = str(path.relative_to(workspace_path)) if path != workspace_path else ""
        
        node = {
            "name": path.name or workspace_path.name,
            "path": rel_path,
            "is_directory": path.is_dir(),
        }
        
        if path.is_dir() and current_depth < max_depth:
            children = []
            try:
                for item in sorted(path.iterdir()):
                    # Skip hidden files and common ignore patterns
                    if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules', '.git']:
                        continue
                    children.append(build_tree(item, current_depth + 1))
            except PermissionError:
                pass
            node["children"] = children
        elif path.is_file():
            node["size"] = path.stat().st_size
        
        return node
    
    return build_tree(workspace_path, 0)
