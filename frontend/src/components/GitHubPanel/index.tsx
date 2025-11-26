/**
 * GitHubPanel - 重构版本
 * 整合多个子组件，提供完整的 GitHub 集成功能
 */

import { useState, useEffect } from 'react';
import {
    Github,
    GitCommit,
    GitBranch,
    GitPullRequest,
    Settings,
} from 'lucide-react';
import { useSessionStore } from '../../hooks/useSession';
import { githubApi } from '../../services/api';
import { RepoInfo } from './RepoInfo';
import { ChangesView } from './ChangesView';
import { BranchManager } from './BranchManager';
import { CreatePRDialog } from './CreatePRDialog';
import { GitHubSettings } from '../GitHubSettings';
import type { FileChange } from '../../types';

type TabType = 'repo' | 'changes' | 'branch' | 'pr';

export function GitHubPanel() {
    const { currentSession, fetchFiles, fetchSessions } = useSessionStore();
    const [activeTab, setActiveTab] = useState<TabType>('repo');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // State
    const [changes, setChanges] = useState<FileChange[]>([]);
    const [branches, setBranches] = useState<string[]>([]);
    const [showPRDialog, setShowPRDialog] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const sessionId = currentSession?.id;
    const hasRepo = !!currentSession?.github_repo_url;

    // 显示成功消息，3秒后自动消失
    const showSuccess = (message: string) => {
        setSuccessMessage(message);
        setError(null);
        setTimeout(() => setSuccessMessage(null), 3000);
    };

    // Load data when session changes or tab changes
    useEffect(() => {
        if (sessionId && hasRepo) {
            if (activeTab === 'changes') {
                loadChanges();
            } else if (activeTab === 'branch') {
                loadBranches();
            }
        }
    }, [sessionId, hasRepo, activeTab]);

    const loadChanges = async () => {
        if (!sessionId) return;
        try {
            const data = await githubApi.getChanges(sessionId);
            setChanges(data);
        } catch (err) {
            console.error('Failed to load changes:', err);
            setError('Failed to load changes');
        }
    };

    const loadBranches = async () => {
        if (!sessionId) return;
        try {
            const data = await githubApi.listBranches(sessionId);
            setBranches(data);
        } catch (err) {
            console.error('Failed to load branches:', err);
            setError('Failed to load branches');
        }
    };

    const handlePull = async () => {
        if (!sessionId) return;
        setIsLoading(true);
        setError(null);
        setSuccessMessage(null);

        try {
            await githubApi.pull(sessionId);
            await fetchFiles();
            if (activeTab === 'changes') {
                await loadChanges();
            }
            showSuccess('Pull 成功！已获取最新代码');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Pull failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handlePush = async () => {
        if (!sessionId) return;
        setIsLoading(true);
        setError(null);
        setSuccessMessage(null);

        try {
            await githubApi.push(sessionId);
            showSuccess('Push 成功！代码已推送到远程仓库');
            // 刷新变更列表
            if (activeTab === 'changes') {
                await loadChanges();
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Push failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCommit = async (message: string, files?: string[]) => {
        if (!sessionId) return;

        setIsLoading(true);
        setError(null);
        setSuccessMessage(null);

        try {
            await githubApi.commit(sessionId, message, files);
            await loadChanges();
            showSuccess('Commit 成功！');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Commit failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateBranch = async (branchName: string, checkout: boolean) => {
        if (!sessionId) return;

        setIsLoading(true);
        setError(null);

        try {
            await githubApi.createBranch(sessionId, branchName, checkout);
            await loadBranches();
            await fetchSessions();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Create branch failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCheckout = async (branch: string) => {
        if (!sessionId) return;

        setIsLoading(true);
        setError(null);

        try {
            await githubApi.checkout(sessionId, branch);
            await fetchFiles();
            await fetchSessions();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Checkout failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreatePR = async (
        title: string,
        body: string,
        headBranch: string,
        baseBranch: string
    ) => {
        if (!sessionId) return;

        setIsLoading(true);
        setError(null);

        try {
            await githubApi.createPR(sessionId, title, body, headBranch, baseBranch);
            setShowPRDialog(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Create PR failed');
            throw err; // Re-throw to let dialog handle it
        } finally {
            setIsLoading(false);
        }
    };

    if (!currentSession) {
        return (
            <div className="p-3 text-sm text-editor-muted">
                Select a session to manage GitHub
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Header with Settings */}
            <div className="flex items-center justify-between p-2 border-b border-editor-border">
                <div className="flex items-center gap-1">
                    <Github size={14} className="text-editor-muted" />
                    <span className="text-xs font-medium">GitHub</span>
                </div>
                <button
                    onClick={() => setShowSettings(true)}
                    className="p-1 rounded hover:bg-editor-border transition-colors"
                    title="设置"
                >
                    <Settings size={14} />
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-editor-border">
                <TabButton
                    active={activeTab === 'repo'}
                    onClick={() => setActiveTab('repo')}
                    icon={<Github size={12} />}
                    label="仓库"
                />
                <TabButton
                    active={activeTab === 'changes'}
                    onClick={() => setActiveTab('changes')}
                    icon={<GitCommit size={12} />}
                    label={`变更${changes.length > 0 ? ` (${changes.length})` : ''}`}
                />
                <TabButton
                    active={activeTab === 'branch'}
                    onClick={() => setActiveTab('branch')}
                    icon={<GitBranch size={12} />}
                    label="分支"
                />
                <TabButton
                    active={activeTab === 'pr'}
                    onClick={() => setActiveTab('pr')}
                    icon={<GitPullRequest size={12} />}
                    label="PR"
                />
            </div>

            {/* Success Display */}
            {successMessage && (
                <div className="mx-3 mt-2 px-2 py-1.5 bg-editor-success/20 text-editor-success text-xs rounded flex items-center gap-1.5">
                    <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {successMessage}
                </div>
            )}

            {/* Error Display */}
            {error && (
                <div className="mx-3 mt-2 px-2 py-1.5 bg-editor-error/20 text-editor-error text-xs rounded">
                    {error}
                </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                {!hasRepo && (
                    <div className="p-3 text-xs text-editor-muted">
                        此会话未绑定 GitHub 仓库。创建新会话时可以选择仓库。
                    </div>
                )}

                {hasRepo && activeTab === 'repo' && (
                    <RepoInfo
                        repoUrl={currentSession.github_repo_url!}
                        branch={currentSession.github_branch || 'main'}
                        onPull={handlePull}
                        isLoading={isLoading}
                    />
                )}

                {hasRepo && activeTab === 'changes' && (
                    <ChangesView
                        sessionId={sessionId!}
                        changes={changes}
                        onRefresh={loadChanges}
                        onCommit={handleCommit}
                        onPush={handlePush}
                        isLoading={isLoading}
                    />
                )}

                {hasRepo && activeTab === 'branch' && (
                    <BranchManager
                        sessionId={sessionId!}
                        currentBranch={currentSession.github_branch || 'main'}
                        branches={branches}
                        onCreateBranch={handleCreateBranch}
                        onCheckout={handleCheckout}
                        isLoading={isLoading}
                    />
                )}

                {hasRepo && activeTab === 'pr' && (
                    <div className="p-3 space-y-3">
                        <button
                            onClick={() => setShowPRDialog(true)}
                            className="w-full px-3 py-2 text-sm bg-editor-accent text-editor-panel rounded flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
                        >
                            <GitPullRequest size={16} />
                            创建 Pull Request
                        </button>
                        <div className="text-xs text-editor-muted">
                            PR 列表功能待实现
                        </div>
                    </div>
                )}
            </div>

            {/* Dialogs */}
            {showPRDialog && hasRepo && (
                <CreatePRDialog
                    sessionId={sessionId!}
                    currentBranch={currentSession.github_branch || 'main'}
                    branches={branches.length > 0 ? branches : ['main']}
                    onClose={() => setShowPRDialog(false)}
                    onCreate={handleCreatePR}
                />
            )}

            {showSettings && (
                <GitHubSettings onClose={() => setShowSettings(false)} />
            )}
        </div>
    );
}

function TabButton({
    active,
    onClick,
    icon,
    label
}: {
    active: boolean;
    onClick: () => void;
    icon: React.ReactNode;
    label: string;
}) {
    return (
        <button
            onClick={onClick}
            className={`
        flex-1 px-2 py-1.5 text-xs flex items-center justify-center gap-1
        border-b-2 transition-colors
        ${active
                    ? 'border-editor-accent text-editor-accent'
                    : 'border-transparent text-editor-muted hover:text-editor-text'
                }
      `}
        >
            {icon}
            {label}
        </button>
    );
}

