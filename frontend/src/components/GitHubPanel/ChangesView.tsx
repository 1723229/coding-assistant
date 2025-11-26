/**
 * ChangesView - 代码变更视图组件
 * 显示文件变更列表、diff查看、提交和推送
 * 
 * 工作流程：
 * 1. 查看变更文件列表
 * 2. 选择要提交的文件（可选，默认全部）
 * 3. 输入 Commit Message（必填）
 * 4. 点击「提交」将变更提交到本地仓库
 * 5. 点击「推送」将本地提交推送到远程仓库
 */

import { useState, useEffect } from 'react';
import { Check, RefreshCw, ChevronRight, ChevronDown, Maximize2, Minimize2, Loader2, Upload, X, GitCommit, CloudUpload } from 'lucide-react';
import { githubApi } from '../../services/api';
import { DiffViewer } from './DiffViewer';
import type { FileChange } from '../../types';

interface ChangesViewProps {
    sessionId: string;
    changes: FileChange[];
    onRefresh: () => void;
    onCommit: (message: string, files?: string[]) => Promise<void>;
    onPush: () => Promise<void>;
    isLoading: boolean;
}

export function ChangesView({ sessionId, changes, onRefresh, onCommit, onPush, isLoading }: ChangesViewProps) {
    const [commitMessage, setCommitMessage] = useState('');
    const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
    const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
    const [fileDiffs, setFileDiffs] = useState<Record<string, string>>({});
    const [loadingDiffs, setLoadingDiffs] = useState<Set<string>>(new Set());
    const [modalFile, setModalFile] = useState<{ path: string; diff: string } | null>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [commitError, setCommitError] = useState<string | null>(null);
    const [lastCommitSuccess, setLastCommitSuccess] = useState(false);

    const toggleFileSelection = (path: string) => {
        const newSelection = new Set(selectedFiles);
        if (newSelection.has(path)) {
            newSelection.delete(path);
        } else {
            newSelection.add(path);
        }
        setSelectedFiles(newSelection);
    };

    const toggleAllFiles = () => {
        if (selectedFiles.size === changes.length) {
            setSelectedFiles(new Set());
        } else {
            setSelectedFiles(new Set(changes.map(c => c.path)));
        }
    };

    const toggleFileExpanded = async (path: string) => {
        const newExpanded = new Set(expandedFiles);
        if (newExpanded.has(path)) {
            newExpanded.delete(path);
        } else {
            newExpanded.add(path);
            // Load diff if not already loaded
            if (!fileDiffs[path] && !loadingDiffs.has(path)) {
                await loadFileDiff(path);
            }
        }
        setExpandedFiles(newExpanded);
    };

    const loadFileDiff = async (path: string) => {
        setLoadingDiffs(prev => new Set(prev).add(path));
        try {
            const result = await githubApi.getFileDiff(sessionId, path);
            setFileDiffs(prev => ({ ...prev, [path]: result.diff }));
        } catch (err) {
            console.error('Failed to load diff:', err);
            setFileDiffs(prev => ({ ...prev, [path]: '// 加载 diff 失败' }));
        } finally {
            setLoadingDiffs(prev => {
                const newSet = new Set(prev);
                newSet.delete(path);
                return newSet;
            });
        }
    };

    const openDiffModal = async (path: string) => {
        // Load diff if not already loaded
        if (!fileDiffs[path]) {
            await loadFileDiff(path);
        }
        setModalFile({ path, diff: fileDiffs[path] || '' });
    };

    // Update modal diff when fileDiffs changes
    useEffect(() => {
        if (modalFile && fileDiffs[modalFile.path]) {
            setModalFile(prev => prev ? { ...prev, diff: fileDiffs[prev.path] || '' } : null);
        }
    }, [fileDiffs]);

    const handleCommit = async () => {
        setCommitError(null);

        if (!commitMessage.trim()) {
            setCommitError('请输入提交信息');
            return;
        }

        const filesToCommit = selectedFiles.size > 0
            ? Array.from(selectedFiles)
            : undefined;

        try {
            await onCommit(commitMessage, filesToCommit);
            setCommitMessage('');
            setSelectedFiles(new Set());
            setLastCommitSuccess(true);
            setTimeout(() => setLastCommitSuccess(false), 3000);
        } catch (err) {
            setCommitError(err instanceof Error ? err.message : '提交失败');
        }
    };

    const handlePush = async () => {
        setCommitError(null);
        try {
            await onPush();
        } catch (err) {
            setCommitError(err instanceof Error ? err.message : '推送失败');
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'added': return 'text-green-400';
            case 'modified': return 'text-yellow-400';
            case 'deleted': return 'text-red-400';
            case 'renamed': return 'text-blue-400';
            default: return 'text-editor-muted';
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'added': return 'A';
            case 'modified': return 'M';
            case 'deleted': return 'D';
            case 'renamed': return 'R';
            default: return '?';
        }
    };

    const getStatusBgColor = (status: string) => {
        switch (status) {
            case 'added': return 'bg-green-500/10';
            case 'modified': return 'bg-yellow-500/10';
            case 'deleted': return 'bg-red-500/10';
            case 'renamed': return 'bg-blue-500/10';
            default: return '';
        }
    };

    // Fullscreen modal for all changes
    if (isFullscreen) {
        return (
            <div className="fixed inset-0 z-50 bg-editor-panel flex flex-col">
                {/* Fullscreen Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-editor-border bg-editor-bg">
                    <div className="flex items-center gap-3">
                        <GitCommit size={18} className="text-editor-accent" />
                        <span className="font-medium">代码变更</span>
                        <span className="text-sm text-editor-muted">
                            ({changes.length} 个文件)
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={onRefresh}
                            className="p-2 rounded hover:bg-editor-border transition-colors"
                            title="刷新"
                            disabled={isLoading}
                        >
                            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
                        </button>
                        <button
                            onClick={() => setIsFullscreen(false)}
                            className="p-2 rounded hover:bg-editor-border transition-colors"
                            title="退出全屏"
                        >
                            <Minimize2 size={16} />
                        </button>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1 flex overflow-hidden">
                    {/* File List - Left Panel */}
                    <div className="w-80 border-r border-editor-border flex flex-col">
                        {/* Select All */}
                        <div className="flex items-center gap-2 px-4 py-3 border-b border-editor-border bg-editor-bg">
                            <input
                                type="checkbox"
                                checked={selectedFiles.size === changes.length && changes.length > 0}
                                onChange={toggleAllFiles}
                                className="w-4 h-4"
                            />
                            <span className="text-sm text-editor-muted">
                                全选 ({selectedFiles.size}/{changes.length})
                            </span>
                        </div>

                        {/* File List */}
                        <div className="flex-1 overflow-y-auto">
                            {changes.map((change) => {
                                const isSelected = selectedFiles.has(change.path);
                                const isDiffLoading = loadingDiffs.has(change.path);

                                return (
                                    <div
                                        key={change.path}
                                        className={`flex items-center gap-3 px-4 py-3 border-b border-editor-border hover:bg-editor-bg cursor-pointer transition-colors ${getStatusBgColor(change.status)}`}
                                        onClick={() => openDiffModal(change.path)}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={(e) => {
                                                e.stopPropagation();
                                                toggleFileSelection(change.path);
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                            className="w-4 h-4"
                                        />
                                        <span className={`text-sm font-mono font-bold ${getStatusColor(change.status)}`}>
                                            {getStatusLabel(change.status)}
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm truncate" title={change.path}>
                                                {change.path.split('/').pop()}
                                            </div>
                                            <div className="text-xs text-editor-muted truncate">
                                                {change.path}
                                            </div>
                                        </div>
                                        {isDiffLoading && <Loader2 size={14} className="animate-spin" />}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Diff Preview - Right Panel */}
                    <div className="flex-1 flex flex-col overflow-hidden">
                        {modalFile ? (
                            <>
                                <div className="px-4 py-3 border-b border-editor-border bg-editor-bg flex items-center justify-between">
                                    <span className="font-mono text-sm">{modalFile.path}</span>
                                    <button
                                        onClick={() => setModalFile(null)}
                                        className="p-1 rounded hover:bg-editor-border"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                                <div className="flex-1 overflow-auto p-4">
                                    <DiffViewer
                                        diff={modalFile.diff}
                                        fileName={modalFile.path.split('/').pop() || modalFile.path}
                                    />
                                </div>
                            </>
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-editor-muted">
                                点击左侧文件查看差异
                            </div>
                        )}
                    </div>
                </div>

                {/* Bottom Action Bar */}
                <div className="border-t border-editor-border bg-editor-bg p-4">
                    {/* Error/Success Messages */}
                    {commitError && (
                        <div className="mb-3 px-3 py-2 bg-red-500/20 text-red-400 text-sm rounded">
                            {commitError}
                        </div>
                    )}
                    {lastCommitSuccess && (
                        <div className="mb-3 px-3 py-2 bg-green-500/20 text-green-400 text-sm rounded">
                            ✓ 提交成功！现在可以推送到远程仓库
                        </div>
                    )}

                    <div className="flex items-end gap-4">
                        {/* Commit Message */}
                        <div className="flex-1">
                            <label className="block text-xs text-editor-muted mb-1">
                                提交信息 <span className="text-red-400">*</span>
                            </label>
                            <textarea
                                value={commitMessage}
                                onChange={(e) => setCommitMessage(e.target.value)}
                                placeholder="描述你的更改..."
                                rows={2}
                                className="w-full px-3 py-2 text-sm bg-editor-panel border border-editor-border rounded resize-none focus:outline-none focus:border-editor-accent"
                            />
                        </div>

                        {/* Actions */}
                        <div className="flex flex-col gap-2">
                            <button
                                onClick={handleCommit}
                                disabled={isLoading || !commitMessage.trim() || changes.length === 0}
                                className="px-4 py-2 text-sm bg-green-600 text-white rounded flex items-center justify-center gap-2 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                title="将选中的文件提交到本地仓库"
                            >
                                <Check size={16} />
                                提交到本地 {selectedFiles.size > 0 ? `(${selectedFiles.size})` : '(全部)'}
                            </button>
                            <button
                                onClick={handlePush}
                                disabled={isLoading}
                                className="px-4 py-2 text-sm bg-blue-600 text-white rounded flex items-center justify-center gap-2 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                title="将本地提交推送到远程仓库"
                            >
                                <CloudUpload size={16} />
                                推送到远程
                            </button>
                        </div>
                    </div>

                    {/* Help Text */}
                    <div className="mt-3 text-xs text-editor-muted">
                        <span className="font-medium">提示：</span>
                        先「提交到本地」保存更改，再「推送到远程」同步到 GitHub
                    </div>
                </div>
            </div>
        );
    }

    // Normal (compact) view
    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-editor-border">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium">本地变更</span>
                    <span className="text-xs text-editor-muted">
                        ({changes.length})
                    </span>
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setIsFullscreen(true)}
                        className="p-1 rounded hover:bg-editor-border transition-colors"
                        title="全屏查看"
                    >
                        <Maximize2 size={12} />
                    </button>
                    <button
                        onClick={onRefresh}
                        className="p-1 rounded hover:bg-editor-border transition-colors"
                        title="刷新"
                        disabled={isLoading}
                    >
                        <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Changes List */}
            <div className="flex-1 overflow-y-auto">
                {changes.length === 0 ? (
                    <div className="text-center text-editor-muted text-xs py-8">
                        没有本地变更
                    </div>
                ) : (
                    <div>
                        {/* Select All */}
                        <div className="flex items-center gap-2 px-3 py-2 border-b border-editor-border bg-editor-bg">
                            <input
                                type="checkbox"
                                checked={selectedFiles.size === changes.length && changes.length > 0}
                                onChange={toggleAllFiles}
                                className="w-3 h-3"
                            />
                            <span className="text-xs text-editor-muted">
                                全选 ({selectedFiles.size}/{changes.length})
                            </span>
                        </div>

                        {/* File List */}
                        {changes.map((change) => {
                            const isExpanded = expandedFiles.has(change.path);
                            const isSelected = selectedFiles.has(change.path);
                            const isDiffLoading = loadingDiffs.has(change.path);
                            const diff = fileDiffs[change.path];

                            return (
                                <div key={change.path} className="border-b border-editor-border">
                                    {/* File Header */}
                                    <div className={`flex items-center gap-2 px-3 py-2 hover:bg-editor-bg transition-colors ${getStatusBgColor(change.status)}`}>
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => toggleFileSelection(change.path)}
                                            className="w-3 h-3"
                                        />
                                        <button
                                            onClick={() => toggleFileExpanded(change.path)}
                                            className="p-0.5 rounded hover:bg-editor-border transition-colors"
                                        >
                                            {isDiffLoading ? (
                                                <Loader2 size={12} className="animate-spin" />
                                            ) : isExpanded ? (
                                                <ChevronDown size={12} />
                                            ) : (
                                                <ChevronRight size={12} />
                                            )}
                                        </button>
                                        <span
                                            className={`text-xs font-mono font-semibold ${getStatusColor(change.status)}`}
                                        >
                                            {getStatusLabel(change.status)}
                                        </span>
                                        <span className="text-xs truncate flex-1" title={change.path}>
                                            {change.path.split('/').pop()}
                                        </span>
                                        {/* Expand button */}
                                        <button
                                            onClick={() => openDiffModal(change.path)}
                                            className="p-1 rounded hover:bg-editor-border transition-colors opacity-60 hover:opacity-100"
                                            title="放大查看"
                                        >
                                            <Maximize2 size={12} />
                                        </button>
                                    </div>

                                    {/* File Details (when expanded) */}
                                    {isExpanded && (
                                        <div className="px-3 py-2 bg-editor-panel max-h-48 overflow-y-auto">
                                            <div className="text-xs text-editor-muted mb-2 font-mono truncate" title={change.path}>
                                                {change.path}
                                            </div>
                                            {isDiffLoading ? (
                                                <div className="flex items-center gap-2 text-xs text-editor-muted py-4">
                                                    <Loader2 size={14} className="animate-spin" />
                                                    加载中...
                                                </div>
                                            ) : diff ? (
                                                <DiffViewer
                                                    diff={diff}
                                                    fileName={change.path.split('/').pop() || change.path}
                                                />
                                            ) : (
                                                <div className="text-xs text-editor-muted italic py-2">
                                                    无 diff 内容
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Commit & Push Section */}
            <div className="border-t border-editor-border p-3 space-y-2 bg-editor-bg">
                {/* Error Message */}
                {commitError && (
                    <div className="px-2 py-1.5 bg-red-500/20 text-red-400 text-xs rounded">
                        {commitError}
                    </div>
                )}
                {/* Success Message */}
                {lastCommitSuccess && (
                    <div className="px-2 py-1.5 bg-green-500/20 text-green-400 text-xs rounded">
                        ✓ 提交成功！
                    </div>
                )}

                {/* Commit Message */}
                <div>
                    <label className="block text-xs text-editor-muted mb-1">
                        提交信息 <span className="text-red-400">*</span>
                    </label>
                    <textarea
                        value={commitMessage}
                        onChange={(e) => setCommitMessage(e.target.value)}
                        placeholder="描述你的更改..."
                        rows={2}
                        className="w-full px-2 py-1.5 text-xs bg-editor-panel border border-editor-border rounded resize-none focus:outline-none focus:border-editor-accent"
                    />
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                    <button
                        onClick={handleCommit}
                        disabled={isLoading || !commitMessage.trim() || changes.length === 0}
                        className="flex-1 px-2 py-1.5 text-xs bg-green-600 text-white rounded flex items-center justify-center gap-1 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="将选中的文件提交到本地仓库"
                    >
                        <Check size={12} />
                        提交 {selectedFiles.size > 0 ? `(${selectedFiles.size})` : ''}
                    </button>
                    <button
                        onClick={handlePush}
                        disabled={isLoading}
                        className="flex-1 px-2 py-1.5 text-xs bg-blue-600 text-white rounded flex items-center justify-center gap-1 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="将本地提交推送到远程仓库"
                    >
                        <Upload size={12} />
                        推送
                    </button>
                </div>

                {/* Help Text */}
                <div className="text-xs text-editor-muted text-center">
                    先提交 → 再推送
                </div>
            </div>

            {/* Diff Modal */}
            {modalFile && !isFullscreen && (
                <DiffViewer
                    diff={modalFile.diff}
                    fileName={modalFile.path.split('/').pop() || modalFile.path}
                    onClose={() => setModalFile(null)}
                    isModal
                />
            )}
        </div>
    );
}
