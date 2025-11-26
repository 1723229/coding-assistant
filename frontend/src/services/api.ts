import type {
    Session,
    CreateSessionRequest,
    Message,
    FileInfo,
    FileContent,
    RepoInfo,
    FileChange,
    FileDiff,
    PullRequest,
    GitHubToken
} from '../types';

const API_BASE = '/api/code';

// Response interface matching backend BaseResponse
interface ApiResponse<T> {
    code: number;
    message: string;
    data: T;
}

// List response interface
interface ListApiResponse<T> {
    code: number;
    message: string;
    data: {
        items: T[];
        total: number;
        page?: number;
        size?: number;
    };
}

// Helper for API calls with BaseResponse handling
async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
        ...options,
    });

    const result = await response.json().catch(() => ({ code: 500, message: 'Unknown error', data: null }));

    // Handle BaseResponse format
    if ('code' in result && 'message' in result && 'data' in result) {
        if (result.code !== 200 && result.code !== 201) {
            throw new Error(result.message || `Error code: ${result.code}`);
        }
        return result.data as T;
    }

    // Old format fallback
    if (!response.ok) {
        const error = result.detail || result.message || 'Unknown error';
        throw new Error(typeof error === 'string' ? error : `HTTP ${response.status}`);
    }

    return result as T;
}

// Helper for list API calls
async function fetchList<T>(url: string, options?: RequestInit): Promise<T[]> {
    const response = await fetch(`${API_BASE}${url}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
        ...options,
    });

    const result = await response.json().catch(() => ({ code: 500, message: 'Unknown error', data: { items: [] } }));

    // Handle new ListResponse format
    if ('code' in result && 'data' in result && result.data && 'items' in result.data) {
        if (result.code !== 200) {
            throw new Error(result.message || `Error code: ${result.code}`);
        }
        return result.data.items as T[];
    }

    // Handle BaseResponse with array data
    if ('code' in result && 'data' in result && Array.isArray(result.data)) {
        if (result.code !== 200) {
            throw new Error(result.message || `Error code: ${result.code}`);
        }
        return result.data as T[];
    }

    // Old format fallback (direct array)
    if (!response.ok) {
        const error = result.detail || result.message || 'Unknown error';
        throw new Error(typeof error === 'string' ? error : `HTTP ${response.status}`);
    }

    return Array.isArray(result) ? result as T[] : [];
}

// Session API
export const sessionApi = {
    list: () => fetchList<Session>('/sessions'),

    create: (data: CreateSessionRequest) =>
        fetchJson<Session>('/sessions', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    get: (id: string) => fetchJson<Session>(`/sessions/${id}`),

    update: (id: string, data: Partial<Session>) =>
        fetchJson<Session>(`/sessions/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    delete: (id: string) =>
        fetchJson<{ status: string; session_id: string }>(`/sessions/${id}`, {
            method: 'DELETE',
        }),

    getMessages: (id: string) => fetchList<Message>(`/sessions/${id}/messages`),
};

// Chat API
export const chatApi = {
    getHistory: (sessionId: string) => fetchList<Message>(`/chat/history/${sessionId}`),

    getStats: (sessionId: string) => fetchJson<{
        session_id: string;
        total_messages: number;
        user_messages: number;
        assistant_messages: number;
        tool_uses: number;
    }>(`/chat/stats/${sessionId}`),

    getAllStats: () => fetchJson<{
        total_sessions: number;
        active_sessions: number;
        total_messages: number;
    }>('/chat/stats'),

    createWebSocket: (sessionId: string): WebSocket => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return new WebSocket(`${protocol}//${host}/api/chat/ws/${sessionId}`);
    },
};

// Workspace API
export const workspaceApi = {
    listFiles: (sessionId: string, path = '') =>
        fetchList<FileInfo>(`/workspace/${sessionId}/files?path=${encodeURIComponent(path)}`),

    getFileContent: (sessionId: string, path: string) =>
        fetchJson<FileContent>(`/workspace/${sessionId}/file?path=${encodeURIComponent(path)}`),

    writeFileContent: (sessionId: string, path: string, content: string) =>
        fetchJson<{ path: string; size: number }>(`/workspace/${sessionId}/file`, {
            method: 'PUT',
            body: JSON.stringify({ path, content }),
        }),

    deleteFile: (sessionId: string, path: string) =>
        fetchJson<{ path: string }>(`/workspace/${sessionId}/file?path=${encodeURIComponent(path)}`, {
            method: 'DELETE',
        }),
};

// GitHub API
export const githubApi = {
    // Token management
    listTokens: () => fetchList<GitHubToken>('/github/tokens'),

    addToken: (platform: string, domain: string, token: string) =>
        fetchJson<GitHubToken>('/github/tokens', {
            method: 'POST',
            body: JSON.stringify({ platform, domain, token }),
        }),

    deleteToken: (tokenId: string) =>
        fetchJson<{ id: string }>(`/github/tokens/${tokenId}`, {
            method: 'DELETE',
        }),

    // Repository operations
    listUserRepos: (query?: string, page = 1, perPage = 30) => {
        let endpoint = `/github/repos?page=${page}&per_page=${perPage}`;
        if (query) endpoint += `&query=${encodeURIComponent(query)}`;
        return fetchList<RepoInfo>(endpoint);
    },

    getRepoInfo: (url: string) =>
        fetchJson<RepoInfo>(`/github/repos/info?repo_url=${encodeURIComponent(url)}`),

    cloneRepo: (sessionId: string, repoUrl: string, branch?: string) =>
        fetchJson<{ repo_url: string; branch: string }>(`/github/${sessionId}/clone`, {
            method: 'POST',
            body: JSON.stringify({ repo_url: repoUrl, branch }),
        }),

    // Local Git operations
    getChanges: (sessionId: string, includeDiff = false) =>
        fetchList<FileChange>(`/github/${sessionId}/changes?include_diff=${includeDiff}`),

    getFileDiff: (sessionId: string, filePath: string) =>
        fetchJson<FileDiff>(`/github/${sessionId}/diff?file_path=${encodeURIComponent(filePath)}`),

    commit: (sessionId: string, message: string, files?: string[]) =>
        fetchJson<{ commit_sha: string }>(`/github/${sessionId}/commit`, {
            method: 'POST',
            body: JSON.stringify({ message, files }),
        }),

    push: (sessionId: string, branch?: string) =>
        fetchJson<{ message: string }>(`/github/${sessionId}/push`, {
            method: 'POST',
            body: JSON.stringify({ branch }),
        }),

    pull: (sessionId: string) =>
        fetchJson<{ message: string }>(`/github/${sessionId}/pull`, {
            method: 'POST',
        }),

    // Branch operations
    listBranches: (sessionId: string) =>
        fetchList<{ name: string; is_current: boolean; commit_sha: string }>(`/github/${sessionId}/branches`),

    createBranch: (sessionId: string, branchName: string, checkout = true) =>
        fetchJson<{ branch_name: string }>(`/github/${sessionId}/branches`, {
            method: 'POST',
            body: JSON.stringify({ branch_name: branchName, checkout }),
        }),

    checkout: (sessionId: string, branchName: string) =>
        fetchJson<{ branch_name: string }>(`/github/${sessionId}/checkout`, {
            method: 'POST',
            body: JSON.stringify({ branch_name: branchName }),
        }),

    // Pull request
    createPR: (sessionId: string, title: string, body: string, headBranch: string, baseBranch?: string) =>
        fetchJson<PullRequest>(`/github/${sessionId}/pull-request`, {
            method: 'POST',
            body: JSON.stringify({
                title,
                body,
                head_branch: headBranch,
                base_branch: baseBranch,
            }),
        }),
};
