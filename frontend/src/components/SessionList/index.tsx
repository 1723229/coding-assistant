import { useState } from 'react';
import { Plus, Trash2, MessageSquare, Github, Search } from 'lucide-react';
import { useSessionStore } from '../../hooks/useSession';
import { RepoSelector } from '../RepoSelector';
import type { Session, RepoInfo } from '../../types';

export function SessionList() {
    const {
        sessions,
        currentSession,
        createSession,
        selectSession,
        deleteSession,
        isLoadingSessions,
    } = useSessionStore();

    const [isCreating, setIsCreating] = useState(false);
    const [newSessionName, setNewSessionName] = useState('');
    const [selectedRepo, setSelectedRepo] = useState<RepoInfo | null>(null);
    const [showRepoSelector, setShowRepoSelector] = useState(false);

    const handleCreate = async () => {
        if (!newSessionName.trim()) return;

        try {
            const session = await createSession(
                newSessionName,
                selectedRepo?.url,
                selectedRepo?.default_branch
            );
            await selectSession(session);
            setNewSessionName('');
            setSelectedRepo(null);
            setIsCreating(false);
        } catch (error) {
            console.error('Failed to create session:', error);
        }
    };

    const handleRepoSelect = (repo: RepoInfo) => {
        setSelectedRepo(repo);
        setShowRepoSelector(false);
    };

    const handleCancelCreate = () => {
        setIsCreating(false);
        setNewSessionName('');
        setSelectedRepo(null);
    };

    const handleDelete = async (e: React.MouseEvent, session: Session) => {
        e.stopPropagation();
        if (confirm(`Delete session "${session.name}"?`)) {
            await deleteSession(session.id);
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-3 border-b border-editor-border flex items-center justify-between">
                <h2 className="font-semibold text-sm">Sessions</h2>
                <button
                    onClick={() => setIsCreating(true)}
                    className="p-1.5 rounded hover:bg-editor-border transition-colors"
                    title="New Session"
                >
                    <Plus size={16} />
                </button>
            </div>

            {/* Create Form */}
            {isCreating && (
                <div className="p-3 border-b border-editor-border space-y-2">
                    <input
                        type="text"
                        value={newSessionName}
                        onChange={(e) => setNewSessionName(e.target.value)}
                        placeholder="Session name"
                        className="w-full px-2 py-1.5 text-sm bg-editor-bg border border-editor-border rounded focus:outline-none focus:border-editor-accent"
                        autoFocus
                    />

                    {/* Repo Selection */}
                    {selectedRepo ? (
                        <div className="flex items-center gap-2 p-2 bg-editor-bg border border-editor-border rounded">
                            <Github size={14} className="text-editor-muted flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="text-xs font-medium truncate">
                                    {selectedRepo.full_name}
                                </div>
                                <div className="text-xs text-editor-muted">
                                    {selectedRepo.default_branch}
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedRepo(null)}
                                className="p-1 rounded hover:bg-editor-border transition-colors"
                                title="Remove repo"
                            >
                                <Trash2 size={12} />
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={() => setShowRepoSelector(true)}
                            className="w-full px-2 py-1.5 text-sm bg-editor-bg border border-editor-border rounded hover:bg-editor-border transition-colors flex items-center justify-center gap-2"
                        >
                            <Search size={14} />
                            选择仓库 (可选)
                        </button>
                    )}

                    <div className="flex gap-2">
                        <button
                            onClick={handleCreate}
                            className="flex-1 px-2 py-1.5 text-sm bg-editor-accent text-editor-panel rounded hover:opacity-90 transition-opacity"
                        >
                            Create
                        </button>
                        <button
                            onClick={handleCancelCreate}
                            className="px-2 py-1.5 text-sm border border-editor-border rounded hover:bg-editor-border transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Session List */}
            <div className="flex-1 overflow-y-auto scrollbar-thin">
                {isLoadingSessions ? (
                    <div className="p-3 text-sm text-editor-muted">Loading...</div>
                ) : sessions.length === 0 ? (
                    <div className="p-3 text-sm text-editor-muted">No sessions yet</div>
                ) : (
                    sessions.map((session) => (
                        <div
                            key={session.id}
                            onClick={() => selectSession(session)}
                            className={`
                group p-3 cursor-pointer border-b border-editor-border
                hover:bg-editor-bg transition-colors
                ${currentSession?.id === session.id ? 'bg-editor-bg' : ''}
              `}
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-1.5">
                                        <MessageSquare size={14} className="flex-shrink-0 text-editor-muted" />
                                        <span className="text-sm font-medium truncate">
                                            {session.name}
                                        </span>
                                    </div>
                                    {session.github_repo_url && (
                                        <div className="flex items-center gap-1 mt-1">
                                            <Github size={12} className="text-editor-muted" />
                                            <span className="text-xs text-editor-muted truncate">
                                                {session.github_repo_url.split('/').slice(-2).join('/')}
                                            </span>
                                        </div>
                                    )}
                                    <div className="text-xs text-editor-muted mt-1">
                                        {new Date(session.updated_at).toLocaleDateString()}
                                    </div>
                                </div>
                                <button
                                    onClick={(e) => handleDelete(e, session)}
                                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-editor-error/20 hover:text-editor-error transition-all"
                                    title="Delete session"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Repo Selector Dialog */}
            {showRepoSelector && (
                <RepoSelector
                    onSelect={handleRepoSelect}
                    onClose={() => setShowRepoSelector(false)}
                    selectedRepo={selectedRepo}
                />
            )}
        </div>
    );
}

