import { create } from 'zustand';
import type { Session, Message, FileInfo } from '../types';
import { sessionApi, chatApi, workspaceApi } from '../services/api';

interface SessionState {
    // Sessions
    sessions: Session[];
    currentSession: Session | null;
    isLoadingSessions: boolean;

    // Messages
    messages: Message[];
    isLoadingMessages: boolean;

    // Files
    files: FileInfo[];
    currentFile: { path: string; content: string } | null;
    isLoadingFiles: boolean;

    // Actions
    fetchSessions: () => Promise<void>;
    createSession: (name?: string, repoUrl?: string, branch?: string) => Promise<Session>;
    selectSession: (session: Session) => Promise<void>;
    deleteSession: (id: string) => Promise<void>;

    addMessage: (message: Message) => void;
    appendToLastMessage: (text: string) => void;
    clearMessages: () => void;

    fetchFiles: (path?: string) => Promise<void>;
    selectFile: (path: string) => Promise<void>;
    saveFile: (path: string, content: string) => Promise<void>;
    setCurrentFileContent: (content: string) => void;
    closeFile: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
    sessions: [],
    currentSession: null,
    isLoadingSessions: false,

    messages: [],
    isLoadingMessages: false,

    files: [],
    currentFile: null,
    isLoadingFiles: false,

    fetchSessions: async () => {
        set({ isLoadingSessions: true });
        try {
            const sessions = await sessionApi.list();
            set({ sessions, isLoadingSessions: false });
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
            set({ isLoadingSessions: false });
        }
    },

    createSession: async (name = 'New Session', repoUrl, branch) => {
        const session = await sessionApi.create({
            name,
            github_repo_url: repoUrl,
            github_branch: branch
        });
        set(state => ({ sessions: [session, ...state.sessions] }));
        return session;
    },

    selectSession: async (session) => {
        set({ currentSession: session, messages: [], files: [], currentFile: null });

        // Load messages
        set({ isLoadingMessages: true });
        try {
            const history = await chatApi.getHistory(session.id);
            set({ messages: history, isLoadingMessages: false });
        } catch (error) {
            console.error('Failed to fetch messages:', error);
            set({ isLoadingMessages: false });
        }

        // Load files
        get().fetchFiles();
    },

    deleteSession: async (id) => {
        await sessionApi.delete(id);
        set(state => ({
            sessions: state.sessions.filter(s => s.id !== id),
            currentSession: state.currentSession?.id === id ? null : state.currentSession,
        }));
    },

    addMessage: (message) => {
        set(state => ({ messages: [...state.messages, message] }));
    },

    appendToLastMessage: (text) => {
        set(state => {
            const { messages } = state;
            if (messages.length === 0) return state;
            
            const lastIndex = messages.length - 1;
            const lastMessage = messages[lastIndex];
            
            if (lastMessage.role !== 'assistant') return state;
            
            // 只更新最后一条消息，避免重新创建整个数组
            const updatedMessages = messages.slice(0, -1);
            updatedMessages.push({
                ...lastMessage,
                content: lastMessage.content + text,
            });
            
            return { messages: updatedMessages };
        });
    },

    clearMessages: () => {
        set({ messages: [] });
    },

    fetchFiles: async (path = '') => {
        const { currentSession } = get();
        if (!currentSession || !currentSession.id) return;

        set({ isLoadingFiles: true });
        try {
            const files = await workspaceApi.listFiles(currentSession.id, path);
            set({ files, isLoadingFiles: false });
        } catch (error) {
            console.error('Failed to fetch files:', error);
            set({ files: [], isLoadingFiles: false });
        }
    },

    selectFile: async (path) => {
        const { currentSession } = get();
        if (!currentSession || !currentSession.id) return;

        try {
            const file = await workspaceApi.getFileContent(currentSession.id, path);
            set({ currentFile: file });
        } catch (error) {
            console.error('Failed to fetch file content:', error);
        }
    },

    saveFile: async (path, content) => {
        const { currentSession } = get();
        if (!currentSession || !currentSession.id) return;

        await workspaceApi.writeFileContent(currentSession.id, path, content);
        set({ currentFile: { path, content } });
    },

    setCurrentFileContent: (content) => {
        set(state => ({
            currentFile: state.currentFile ? { ...state.currentFile, content } : null,
        }));
    },

    closeFile: () => {
        set({ currentFile: null });
    },
}));

