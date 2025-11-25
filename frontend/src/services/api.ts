import type {
    Session,
    CreateSessionRequest,
    Message,
    FileInfo,
    FileContent,
    RepoInfo,
    FileChange,
    PullRequest,
    GitHubToken
} from '../types';

const API_BASE = '/api';

// Helper for API calls
async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// Session API
export const sessionApi = {
    list: () => fetchJson<Session[]>('/sessions/'),

    create: (data: CreateSessionRequest) =>
        fetchJson<Session>('/sessions/', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    get: (id: string) => fetchJson<Session>(`/sessions/${id}`),

    update: (id: string, data: Partial<Session>) =>
        fetchJson<Session>(`/sessions/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    delete: (id: string) =>
        fetchJson<{ status: string }>(`/sessions/${id}`, {
            method: 'DELETE',
        }),

    getMessages: (id: string) => fetchJson<Message[]>(`/sessions/${id}/messages`),
};

// Chat API
export const chatApi = {
    getHistory: (sessionId: string) => fetchJson<Message[]>(`/chat/history/${sessionId}`),

    createWebSocket: (sessionId: string): WebSocket => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return new WebSocket(`${protocol}//${host}/api/chat/ws/${sessionId}`);
    },
};

// Workspace API
export const workspaceApi = {
    listFiles: (sessionId: string, path = '') =>
        fetchJson<FileInfo[]>(`/workspace/${sessionId}/files?path=${encodeURIComponent(path)}`),

    getFileContent: (sessionId: string, path: string) =>
        fetchJson<FileContent>(`/workspace/${sessionId}/files/content?path=${encodeURIComponent(path)}`),

    writeFileContent: (sessionId: string, path: string, content: string) =>
        fetchJson<FileContent>(`/workspace/${sessionId}/files/content?path=${encodeURIComponent(path)}`, {
            method: 'PUT',
            body: JSON.stringify({ content }),
        }),

    deleteFile: (sessionId: string, path: string) =>
        fetchJson<{ status: string }>(`/workspace/${sessionId}/files?path=${encodeURIComponent(path)}`, {
            method: 'DELETE',
        }),

    createDirectory: (sessionId: string, path: string) =>
        fetchJson<FileInfo>(`/workspace/${sessionId}/files/mkdir?path=${encodeURIComponent(path)}`, {
            method: 'POST',
        }),
};

// GitHub API
export const githubApi = {
    getRepoInfo: (url: string) =>
        fetchJson<RepoInfo>(`/github/repo/info?url=${encodeURIComponent(url)}`),

    cloneRepo: (sessionId: string, repoUrl: string, branch?: string) =>
        fetchJson<{ status: string }>(`/github/${sessionId}/clone`, {
            method: 'POST',
            body: JSON.stringify({ repo_url: repoUrl, branch }),
        }),

    getChanges: (sessionId: string) =>
        fetchJson<FileChange[]>(`/github/${sessionId}/changes`),

    commit: (sessionId: string, message: string, files?: string[]) =>
        fetchJson<{ status: string; sha: string }>(`/github/${sessionId}/commit`, {
            method: 'POST',
            body: JSON.stringify({ message, files }),
        }),

    push: (sessionId: string, remote = 'origin', branch?: string) =>
        fetchJson<{ status: string }>(`/github/${sessionId}/push`, {
            method: 'POST',
            body: JSON.stringify({ remote, branch }),
        }),

    createBranch: (sessionId: string, branchName: string, checkout = true) =>
        fetchJson<{ status: string }>(`/github/${sessionId}/branch`, {
            method: 'POST',
            body: JSON.stringify({ branch_name: branchName, checkout }),
        }),

    listBranches: (sessionId: string) =>
        fetchJson<string[]>(`/github/${sessionId}/branches`),

    checkout: (sessionId: string, branch: string) =>
        fetchJson<{ status: string }>(`/github/${sessionId}/checkout?branch=${encodeURIComponent(branch)}`, {
            method: 'POST',
        }),

    pull: (sessionId: string) =>
        fetchJson<{ status: string }>(`/github/${sessionId}/pull`, {
            method: 'POST',
        }),

    createPR: (sessionId: string, title: string, body: string, headBranch: string, baseBranch?: string) =>
        fetchJson<PullRequest>(`/github/${sessionId}/pr`, {
            method: 'POST',
            body: JSON.stringify({
                title,
                body,
                head_branch: headBranch,
                base_branch: baseBranch,
            }),
        }),

    getRepoContents: (url: string, path = '', ref?: string) => {
        let endpoint = `/github/repo/contents?url=${encodeURIComponent(url)}&path=${encodeURIComponent(path)}`;
        if (ref) endpoint += `&ref=${encodeURIComponent(ref)}`;
        return fetchJson<Array<{ name: string; path: string; type: string; size: number }>>(endpoint);
    },

    getRepoFile: (url: string, path: string, ref?: string) => {
        let endpoint = `/github/repo/file?url=${encodeURIComponent(url)}&path=${encodeURIComponent(path)}`;
        if (ref) endpoint += `&ref=${encodeURIComponent(ref)}`;
        return fetchJson<{ path: string; content: string }>(endpoint);
    },

    // Token management
    listTokens: () => fetchJson<GitHubToken[]>('/github/tokens'),

    addToken: (platform: string, domain: string, token: string) =>
        fetchJson<GitHubToken>('/github/tokens', {
            method: 'POST',
            body: JSON.stringify({ platform, domain, token }),
        }),

    deleteToken: (tokenId: string) =>
        fetchJson<{ status: string }>(`/github/tokens/${tokenId}`, {
            method: 'DELETE',
        }),

    // User repos
    listUserRepos: (query?: string, page = 1) => {
        let endpoint = `/github/user/repos?page=${page}`;
        if (query) endpoint += `&query=${encodeURIComponent(query)}`;
        return fetchJson<RepoInfo[]>(endpoint);
    },
};

