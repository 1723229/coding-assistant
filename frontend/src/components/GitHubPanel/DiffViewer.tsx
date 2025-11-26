/**
 * DiffViewer - Diff 查看组件
 * 支持语法高亮、行号显示、放大模态框查看
 */

import { useState, useMemo } from 'react';
import { X, Maximize2, Copy, Check } from 'lucide-react';

interface DiffViewerProps {
    diff: string;
    fileName: string;
    onClose?: () => void;
    isModal?: boolean;
}

interface DiffLine {
    type: 'header' | 'hunk' | 'addition' | 'deletion' | 'context' | 'empty';
    content: string;
    lineNumberOld?: number;
    lineNumberNew?: number;
}

function parseDiff(diff: string): DiffLine[] {
    if (!diff) return [];
    
    const lines = diff.split('\n');
    const result: DiffLine[] = [];
    
    let oldLine = 0;
    let newLine = 0;
    
    for (const line of lines) {
        if (line.startsWith('diff ') || line.startsWith('index ') || 
            line.startsWith('---') || line.startsWith('+++')) {
            result.push({ type: 'header', content: line });
        } else if (line.startsWith('@@')) {
            // Parse hunk header: @@ -start,count +start,count @@
            const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
            if (match) {
                oldLine = parseInt(match[1], 10);
                newLine = parseInt(match[2], 10);
            }
            result.push({ type: 'hunk', content: line });
        } else if (line.startsWith('+')) {
            result.push({ 
                type: 'addition', 
                content: line.slice(1),
                lineNumberNew: newLine++
            });
        } else if (line.startsWith('-')) {
            result.push({ 
                type: 'deletion', 
                content: line.slice(1),
                lineNumberOld: oldLine++
            });
        } else if (line === '') {
            result.push({ type: 'empty', content: '' });
        } else {
            // Context line (starts with space or is plain text)
            const content = line.startsWith(' ') ? line.slice(1) : line;
            result.push({ 
                type: 'context', 
                content,
                lineNumberOld: oldLine++,
                lineNumberNew: newLine++
            });
        }
    }
    
    return result;
}

function DiffContent({ diff, compact = false }: { diff: string; compact?: boolean }) {
    const lines = useMemo(() => parseDiff(diff), [diff]);
    const [copied, setCopied] = useState(false);
    
    const handleCopy = async () => {
        await navigator.clipboard.writeText(diff);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    
    if (!diff) {
        return (
            <div className="text-editor-muted text-xs italic py-2">
                无变更内容
            </div>
        );
    }
    
    const getLineStyle = (type: DiffLine['type']) => {
        switch (type) {
            case 'addition':
                return 'bg-green-500/15 text-green-400';
            case 'deletion':
                return 'bg-red-500/15 text-red-400';
            case 'hunk':
                return 'bg-blue-500/10 text-blue-400';
            case 'header':
                return 'text-editor-muted';
            default:
                return 'text-editor-text';
        }
    };
    
    const getLinePrefix = (type: DiffLine['type']) => {
        switch (type) {
            case 'addition':
                return '+';
            case 'deletion':
                return '-';
            default:
                return ' ';
        }
    };
    
    return (
        <div className="relative">
            {/* Copy button */}
            <button
                onClick={handleCopy}
                className="absolute top-1 right-1 p-1 rounded bg-editor-bg/80 hover:bg-editor-border transition-colors z-10"
                title="复制 Diff"
            >
                {copied ? <Check size={12} className="text-editor-success" /> : <Copy size={12} />}
            </button>
            
            <div className={`font-mono text-xs overflow-x-auto ${compact ? 'max-h-48' : ''} overflow-y-auto`}>
                {lines.map((line, idx) => (
                    <div 
                        key={idx} 
                        className={`flex ${getLineStyle(line.type)} ${compact ? 'py-0' : 'py-0.5'}`}
                    >
                        {/* Line numbers */}
                        {!compact && line.type !== 'header' && line.type !== 'hunk' && (
                            <>
                                <span className="w-10 text-right pr-2 text-editor-muted select-none shrink-0 border-r border-editor-border/30">
                                    {line.lineNumberOld ?? ''}
                                </span>
                                <span className="w-10 text-right pr-2 text-editor-muted select-none shrink-0 border-r border-editor-border/30">
                                    {line.lineNumberNew ?? ''}
                                </span>
                            </>
                        )}
                        
                        {/* Prefix */}
                        {line.type !== 'header' && line.type !== 'hunk' && (
                            <span className={`w-4 text-center select-none shrink-0 ${
                                line.type === 'addition' ? 'text-green-400' : 
                                line.type === 'deletion' ? 'text-red-400' : 'text-editor-muted'
                            }`}>
                                {getLinePrefix(line.type)}
                            </span>
                        )}
                        
                        {/* Content */}
                        <span className={`flex-1 whitespace-pre ${
                            (line.type === 'header' || line.type === 'hunk') ? 'pl-2' : ''
                        }`}>
                            {line.content || '\u00A0'}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// Modal component for enlarged view
function DiffModal({ diff, fileName, onClose }: { diff: string; fileName: string; onClose: () => void }) {
    // Count additions and deletions
    const stats = useMemo(() => {
        const lines = diff.split('\n');
        let additions = 0;
        let deletions = 0;
        for (const line of lines) {
            if (line.startsWith('+') && !line.startsWith('+++')) additions++;
            if (line.startsWith('-') && !line.startsWith('---')) deletions++;
        }
        return { additions, deletions };
    }, [diff]);
    
    return (
        <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={onClose}
        >
            <div 
                className="bg-editor-panel border border-editor-border rounded-lg shadow-2xl w-[90vw] h-[85vh] flex flex-col"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-editor-border bg-editor-bg rounded-t-lg">
                    <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-medium">{fileName}</span>
                        <div className="flex items-center gap-2 text-xs">
                            <span className="text-green-400">+{stats.additions}</span>
                            <span className="text-red-400">-{stats.deletions}</span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded hover:bg-editor-border transition-colors"
                        title="关闭"
                    >
                        <X size={18} />
                    </button>
                </div>
                
                {/* Content */}
                <div className="flex-1 overflow-auto p-4 bg-editor-bg/50">
                    <DiffContent diff={diff} />
                </div>
            </div>
        </div>
    );
}

export function DiffViewer({ diff, fileName, onClose, isModal = false }: DiffViewerProps) {
    const [showModal, setShowModal] = useState(false);
    
    if (isModal) {
        return <DiffModal diff={diff} fileName={fileName} onClose={onClose!} />;
    }
    
    return (
        <div className="bg-editor-bg/50 rounded border border-editor-border/50 overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-2 py-1 border-b border-editor-border/50 bg-editor-panel/50">
                <span className="text-xs text-editor-muted truncate">{fileName}</span>
                <button
                    onClick={() => setShowModal(true)}
                    className="p-1 rounded hover:bg-editor-border transition-colors"
                    title="放大查看"
                >
                    <Maximize2 size={12} />
                </button>
            </div>
            
            {/* Compact diff view */}
            <div className="p-2">
                <DiffContent diff={diff} compact />
            </div>
            
            {/* Modal */}
            {showModal && (
                <DiffModal 
                    diff={diff} 
                    fileName={fileName} 
                    onClose={() => setShowModal(false)} 
                />
            )}
        </div>
    );
}

export default DiffViewer;

