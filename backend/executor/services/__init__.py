# -*- coding: utf-8 -*-
"""
Executor services module.
"""

from executor.services.agent_service import StreamingAgentService

# Alias for backward compatibility
AgentService = StreamingAgentService

__all__ = ["AgentService", "StreamingAgentService"]
