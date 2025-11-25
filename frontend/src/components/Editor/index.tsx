import { useCallback } from 'react';
import MonacoEditor from '@monaco-editor/react';
import { Save, X, FileCode } from 'lucide-react';
import { useSessionStore } from '../../hooks/useSession';

const LANGUAGE_MAP: Record<string, string> = {
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.py': 'python',
    '.json': 'json',
    '.md': 'markdown',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.xml': 'xml',
    '.sql': 'sql',
    '.sh': 'shell',
    '.bash': 'shell',
    '.rs': 'rust',
    '.go': 'go',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.h': 'cpp',
};

function getLanguage(filename: string): string {
    const ext = filename.slice(filename.lastIndexOf('.'));
    return LANGUAGE_MAP[ext] || 'plaintext';
}

export function Editor() {
    const {
        currentFile,
        currentSession,
        saveFile,
        setCurrentFileContent,
        closeFile,
    } = useSessionStore();

    const handleSave = useCallback(async () => {
        if (!currentFile || !currentSession) return;

        try {
            await saveFile(currentFile.path, currentFile.content);
        } catch (error) {
            console.error('Failed to save file:', error);
        }
    }, [currentFile, currentSession, saveFile]);

    const handleChange = useCallback((value: string | undefined) => {
        if (value !== undefined) {
            setCurrentFileContent(value);
        }
    }, [setCurrentFileContent]);

    // Keyboard shortcuts
    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 's') {
            e.preventDefault();
            handleSave();
        }
    }, [handleSave]);

    if (!currentFile) {
        return (
            <div className="flex-1 flex items-center justify-center bg-editor-bg">
                <div className="text-center text-editor-muted">
                    <FileCode size={48} className="mx-auto mb-4 opacity-50" />
                    <p className="text-sm">请选择具体文件预览</p>
                    <p className="text-xs mt-1">
                        点击左侧文件资源管理器中的文件打开
                    </p>
                </div>
            </div>
        );
    }

    const filename = currentFile.path.split('/').pop() || currentFile.path;
    const language = getLanguage(filename);

    return (
        <div className="flex-1 flex flex-col" onKeyDown={handleKeyDown}>
            {/* Tab Bar */}
            <div className="h-9 bg-editor-panel border-b border-editor-border flex items-center">
                <div className="flex items-center px-3 py-1.5 bg-editor-bg border-r border-editor-border gap-2">
                    <span className="text-sm truncate max-w-[200px]">{filename}</span>
                    <button
                        onClick={closeFile}
                        className="p-0.5 rounded hover:bg-editor-border transition-colors"
                        title="关闭文件"
                    >
                        <X size={14} />
                    </button>
                </div>
                <div className="flex-1" />
                <button
                    onClick={handleSave}
                    className="px-3 py-1 mr-2 text-xs bg-editor-accent text-editor-panel rounded hover:opacity-90 transition-opacity flex items-center gap-1"
                    title="Save (Ctrl+S)"
                >
                    <Save size={12} />
                    Save
                </button>
            </div>

            {/* Editor */}
            <div className="flex-1">
                <MonacoEditor
                    height="100%"
                    language={language}
                    value={currentFile.content}
                    onChange={handleChange}
                    theme="vs-dark"
                    options={{
                        minimap: { enabled: true, maxColumn: 80 },
                        fontSize: 13,
                        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                        fontLigatures: true,
                        lineNumbers: 'on',
                        renderLineHighlight: 'line',
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                        tabSize: 2,
                        wordWrap: 'on',
                        bracketPairColorization: { enabled: true },
                        guides: {
                            indentation: true,
                            bracketPairs: true,
                        },
                        padding: { top: 8 },
                    }}
                />
            </div>

            {/* Status Bar */}
            <div className="h-6 bg-editor-panel border-t border-editor-border flex items-center px-3 text-xs text-editor-muted">
                <span>{language}</span>
                <span className="mx-2">|</span>
                <span>{currentFile.path}</span>
                <span className="flex-1" />
                <span>UTF-8</span>
            </div>
        </div>
    );
}

