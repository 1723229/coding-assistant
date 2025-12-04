# -*- coding: utf-8 -*-
"""
SSE stream proxy for forwarding container responses to clients.

This module handles:
- Proxying SSE streams from executor containers
- Parsing and forwarding events
- Error handling and reconnection
"""

import json
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional

import httpx

from app.core.executor.constants import DEFAULT_STREAM_ENDPOINT
from app.core.executor.container_manager import ContainerInfo
from app.config.settings import ExecutorConfig

logger = logging.getLogger(__name__)


class StreamProxy:
    """
    Proxy for SSE streams from executor containers.
    
    Forwards events from container to client with proper error handling.
    """
    
    def __init__(self, timeout: int = None):
        """
        Initialize stream proxy.
        
        Args:
            timeout: Stream timeout in seconds (defaults to ExecutorConfig.STREAM_TIMEOUT)
        """
        self.timeout = timeout or ExecutorConfig.STREAM_TIMEOUT
    
    async def proxy_stream(
        self,
        container: ContainerInfo,
        task_data: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Proxy SSE stream from container.
        
        Args:
            container: Container information
            task_data: Task data to send to container
            
        Yields:
            dict: Event dictionaries from container
        """
        url = f"{container.api_base_url}{DEFAULT_STREAM_ENDPOINT}"
        
        logger.info(f"Starting stream proxy to {url}")
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=task_data,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Stream request failed: {response.status_code} - {error_text}")
                        yield {
                            "type": "error",
                            "content": f"Stream request failed: {response.status_code}",
                        }
                        return
                    
                    # Parse SSE stream
                    async for event in self._parse_sse_stream(response):
                        yield event
                        
        except httpx.TimeoutException:
            logger.error(f"Stream timeout for container {container.name}")
            yield {
                "type": "error",
                "content": "Stream timeout",
            }
            
        except httpx.ConnectError as e:
            logger.error(f"Connection error to container {container.name}: {e}")
            yield {
                "type": "error",
                "content": f"Connection error: {e}",
            }
            
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for container {container.name}")
            yield {
                "type": "interrupted",
                "message": "Stream cancelled",
            }
            raise
            
        except Exception as e:
            logger.exception(f"Error in stream proxy for container {container.name}")
            yield {
                "type": "error",
                "content": str(e),
            }
    
    async def _parse_sse_stream(
        self,
        response: httpx.Response,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Parse SSE stream from response.
        
        Args:
            response: HTTP response with SSE stream
            
        Yields:
            dict: Parsed event data
        """
        buffer = ""
        
        async for chunk in response.aiter_text():
            buffer += chunk
            
            # Process complete events (ending with \n\n)
            while "\n\n" in buffer:
                event_str, buffer = buffer.split("\n\n", 1)
                
                # Parse event
                event = self._parse_sse_event(event_str)
                if event:
                    yield event
    
    def _parse_sse_event(self, event_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single SSE event.
        
        Args:
            event_str: Raw SSE event string
            
        Returns:
            Parsed event data or None if invalid
        """
        data_lines = []
        event_type = None
        
        for line in event_str.split("\n"):
            line = line.strip()
            
            if line.startswith("data:"):
                data = line[5:].strip()
                data_lines.append(data)
            elif line.startswith("event:"):
                event_type = line[6:].strip()
        
        if not data_lines:
            return None
        
        # Join data lines and parse JSON
        data_str = "".join(data_lines)
        
        try:
            event_data = json.loads(data_str)
            
            # Add event type if present
            if event_type and "type" not in event_data:
                event_data["type"] = event_type
            
            return event_data
            
        except json.JSONDecodeError:
            # Return raw data if not JSON
            return {
                "type": event_type or "raw",
                "content": data_str,
            }


class StreamProxyManager:
    """
    Manager for stream proxy instances.
    
    Tracks active streams and provides cancellation support.
    """
    
    _instance: Optional['StreamProxyManager'] = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._active_streams: Dict[str, asyncio.Task] = {}
        return cls._instance
    
    def register_stream(self, session_id: str, task: asyncio.Task):
        """Register an active stream task."""
        self._active_streams[session_id] = task
    
    def unregister_stream(self, session_id: str):
        """Unregister a stream task."""
        if session_id in self._active_streams:
            del self._active_streams[session_id]
    
    def cancel_stream(self, session_id: str) -> bool:
        """
        Cancel an active stream.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if stream was cancelled
        """
        if session_id in self._active_streams:
            task = self._active_streams[session_id]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled stream for session: {session_id}")
                return True
        return False
    
    def is_streaming(self, session_id: str) -> bool:
        """Check if a session has an active stream."""
        if session_id in self._active_streams:
            return not self._active_streams[session_id].done()
        return False

