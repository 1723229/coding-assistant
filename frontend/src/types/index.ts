// Session types
export interface Session {
    id: string;
    name: string;
    created_at: string;
    updated_at: string;
    is_active: boolean;
    workspace_path: string | null;
    container_id: string | null;
    github_repo_url: string | null;
    github_branch: string | null;
}

export interface CreateSessionRequest {
    name?: string;
    github_repo_url?: string;
    github_branch?: string;
}

// Message types
export interface Message {
    id?: number;
    session_id?: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at?: string;
    tool_name?: string;
}

export interface ChatMessage {
    type: 'text' | 'text_delta' | 'tool_use' | 'tool_result' | 'thinking' | 'system' | 'result' | 'error' | 'connected' | 'user_message_received' | 'response_complete' | 'pong';
    content: string;
    tool_name?: string;
    tool_input?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
    timestamp?: string;
}

// Enhanced event message for better UI display
export interface EventMessage extends Message {
    eventType: 'text' | 'thinking' | 'tool_use' | 'tool_result' | 'system' | 'result' | 'error';
    timestamp: string;
    metadata?: {
        tool_use_id?: string;
        tool_name?: string;
        tool_input?: any;
        duration_ms?: number;
        is_error?: boolean;
        streaming?: boolean;
    };
    isExpanded?: boolean;
}

// File types
export interface FileInfo {
    name: string;
    path: string;
    is_directory: boolean;
    size?: number;
}

export interface FileContent {
    path: string;
    content: string;
}

// GitHub types
export interface GitHubToken {
    id: string;
    platform: 'GitHub' | 'GitLab';
    domain: string;
    token: string; // partially masked
    created_at: string;
}

export interface RepoInfo {
    id?: string;
    name: string;
    owner: string;
    full_name: string;
    url: string;
    default_branch: string;
    description: string | null;
    is_private: boolean;
}

export interface FileChange {
    path: string;
    status: 'added' | 'modified' | 'deleted' | 'renamed';
    additions?: number;
    deletions?: number;
}

export interface PullRequest {
    number: number;
    title: string;
    url: string;
    state: string;
    head_branch: string;
    base_branch: string;
}

// WebSocket message types
export interface WebSocketMessage {
    type: string;
    content?: string;
    message?: string;
    session_id?: string;
    [key: string]: unknown;
}

