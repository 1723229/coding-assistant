/**
 * ChangesView - 代码变更视图组件
 * 显示文件变更列表、diff查看、暂存区管理
 */

import { useState } from 'react';
import { Check, RefreshCw, ChevronRight, ChevronDown } from 'lucide-react';
import type { FileChange } from '../../types';

interface ChangesViewProps {
    sessionId: string;
    changes: FileChange[];
    onRefresh: () => void;
    onCommit: (message: string, files?: string[]) => Promise<void>;
    isLoading: boolean;
}

export function ChangesView({ sessionId, changes, onRefresh, onCommit, isLoading }: ChangesViewProps) {
    const [commitMessage, setCommitMessage] = useState('');
    const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
    const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

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

    const toggleFileExpanded = (path: string) => {
        const newExpanded = new Set(expandedFiles);
        if (newExpanded.has(path)) {
            newExpanded.delete(path);
        } else {
            newExpanded.add(path);
        }
        setExpandedFiles(newExpanded);
    };

    const handleCommit = async () => {
        if (!commitMessage.trim()) return;

        const filesToCommit = selectedFiles.size > 0
            ? Array.from(selectedFiles)
            : undefined;

        await onCommit(commitMessage, filesToCommit);
        setCommitMessage('');
        setSelectedFiles(new Set());
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'added': return 'text-editor-success';
            case 'modified': return 'text-editor-warning';
            case 'deleted': return 'text-editor-error';
            case 'renamed': return 'text-editor-accent';
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
                <button
                    onClick={onRefresh}
                    className="p-1 rounded hover:bg-editor-border transition-colors"
                    title="刷新"
                    disabled={isLoading}
                >
                    <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
                </button>
            </div>

            {/* Changes List */}
            <div className="flex-1 overflow-y-auto">
                {changes.length === 0 ? (
                    <div className="text-center text-editor-muted text-xs py-8">
                        没有变更
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

                            return (
                                <div key={change.path} className="border-b border-editor-border">
                                    {/* File Header */}
                                    <div className="flex items-center gap-2 px-3 py-2 hover:bg-editor-bg transition-colors">
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
                                            {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                        </button>
                                        <span
                                            className={`text-xs font-mono font-semibold ${getStatusColor(change.status)}`}
                                        >
                                            {getStatusLabel(change.status)}
                                        </span>
                                        <span className="text-xs truncate flex-1" title={change.path}>
                                            {change.path.split('/').pop()}
                                        </span>
                                        {change.additions !== undefined && change.deletions !== undefined && (
                                            <div className="flex items-center gap-1 text-xs">
                                                <span className="text-editor-success">+{change.additions}</span>
                                                <span className="text-editor-error">-{change.deletions}</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* File Details (when expanded) */}
                                    {isExpanded && (
                                        <div className="px-3 py-2 bg-editor-panel text-xs font-mono">
                                            <div className="text-editor-muted mb-1">路径: {change.path}</div>
                                            <div className="text-editor-muted">状态: {change.status}</div>
                                            {/* TODO: Add diff view here */}
                                            <div className="mt-2 text-editor-muted italic">
                                                Diff 查看功能待实现
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Commit Section */}
            {changes.length > 0 && (
                <div className="border-t border-editor-border p-3 space-y-2">
                    <textarea
                        value={commitMessage}
                        onChange={(e) => setCommitMessage(e.target.value)}
                        placeholder="Commit message"
                        rows={2}
                        className="w-full px-2 py-1.5 text-xs bg-editor-bg border border-editor-border rounded resize-none focus:outline-none focus:border-editor-accent"
                    />
                    <button
                        onClick={handleCommit}
                        disabled={isLoading || !commitMessage.trim()}
                        className="w-full px-2 py-1.5 text-xs bg-editor-success text-editor-panel rounded flex items-center justify-center gap-1 hover:opacity-90 disabled:opacity-50"
                    >
                        <Check size={12} />
                        提交 {selectedFiles.size > 0 && `(${selectedFiles.size} 个文件)`}
                    </button>
                </div>
            )}
        </div>
    );
}

