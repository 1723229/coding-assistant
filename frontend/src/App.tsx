import { useEffect } from 'react';
import { useSessionStore } from './hooks/useSession';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { SessionList } from './components/SessionList';
import { ChatPanel } from './components/ChatPanel';
import { FileTree } from './components/FileTree';
import { Editor } from './components/Editor';
import { GitHubPanel } from './components/GitHubPanel';

function App() {
    const {
        currentSession,
        fetchSessions,
        isLoadingSessions,
    } = useSessionStore();

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    return (
        <WebSocketProvider>
            <div className="h-screen w-screen flex bg-editor-bg text-editor-text overflow-hidden">
                {/* Left Sidebar - Sessions */}
                <div className="w-64 flex-shrink-0 bg-editor-sidebar border-r border-editor-border flex flex-col">
                    <SessionList />
                </div>

                {/* Main Content */}
                <div className="flex-1 flex flex-col min-w-0">
                    {currentSession ? (
                        <>
                            {/* Top Bar */}
                            <div className="h-10 bg-editor-panel border-b border-editor-border flex items-center px-4 gap-4">
                                <span className="text-sm font-medium truncate">
                                    {currentSession.name}
                                </span>
                                {currentSession.github_repo_url && (
                                    <span className="text-xs text-editor-muted truncate">
                                        {currentSession.github_repo_url}
                                    </span>
                                )}
                            </div>

                            {/* Content Area */}
                            <div className="flex-1 flex min-h-0">
                                {/* File Explorer */}
                                <div className="w-56 flex-shrink-0 bg-editor-sidebar border-r border-editor-border">
                                    <FileTree />
                                </div>

                                {/* Editor Area */}
                                <div className="flex-1 flex flex-col min-w-0">
                                    <Editor />
                                </div>

                                {/* Right Panel - Chat & GitHub */}
                                <div className="w-96 flex-shrink-0 flex flex-col bg-editor-sidebar border-l border-editor-border">
                                    <div className="flex-1 min-h-0">
                                        <ChatPanel />
                                    </div>
                                    <div className="h-64 border-t border-editor-border">
                                        <GitHubPanel />
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-center">
                                <div className="text-6xl mb-4">🤖</div>
                                <h1 className="text-2xl font-bold mb-2">Claude Code Web</h1>
                                <p className="text-editor-muted mb-6">
                                    {isLoadingSessions
                                        ? 'Loading sessions...'
                                        : 'Select or create a session to get started'
                                    }
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </WebSocketProvider>
    );
}

export default App;

