import { useState, useEffect } from 'react';
import { 
  Folder, 
  FolderOpen, 
  File, 
  ChevronRight, 
  ChevronDown,
  RefreshCw,
  FileCode,
  FileJson,
  FileText,
} from 'lucide-react';
import { useSessionStore } from '../../hooks/useSession';
import type { FileInfo } from '../../types';

const FILE_ICONS: Record<string, React.ReactNode> = {
  '.ts': <FileCode size={14} className="text-blue-400" />,
  '.tsx': <FileCode size={14} className="text-blue-400" />,
  '.js': <FileCode size={14} className="text-yellow-400" />,
  '.jsx': <FileCode size={14} className="text-yellow-400" />,
  '.py': <FileCode size={14} className="text-green-400" />,
  '.json': <FileJson size={14} className="text-yellow-300" />,
  '.md': <FileText size={14} className="text-editor-muted" />,
  '.txt': <FileText size={14} className="text-editor-muted" />,
};

function getFileIcon(name: string): React.ReactNode {
  const ext = name.slice(name.lastIndexOf('.'));
  return FILE_ICONS[ext] || <File size={14} className="text-editor-muted" />;
}

export function FileTree() {
  const { 
    currentSession, 
    files, 
    currentFile, 
    fetchFiles, 
    selectFile,
    isLoadingFiles,
  } = useSessionStore();
  
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set(['']));
  const [currentPath, setCurrentPath] = useState('');

  useEffect(() => {
    if (currentSession) {
      fetchFiles(currentPath);
    }
  }, [currentSession, currentPath, fetchFiles]);

  const toggleExpand = async (path: string, isDirectory: boolean) => {
    if (!isDirectory) {
      selectFile(path);
      return;
    }

    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
      setCurrentPath(path);
    }
    setExpandedPaths(newExpanded);
  };

  const handleRefresh = () => {
    fetchFiles(currentPath);
  };

  if (!currentSession) {
    return (
      <div className="p-3 text-sm text-editor-muted">
        Select a session to view files
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-2 border-b border-editor-border flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-editor-muted">
          Explorer
        </span>
        <button
          onClick={handleRefresh}
          disabled={isLoadingFiles}
          className="p-1 rounded hover:bg-editor-border transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw size={14} className={isLoadingFiles ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Breadcrumb */}
      {currentPath && (
        <div className="px-2 py-1 border-b border-editor-border flex items-center gap-1 text-xs">
          <button 
            onClick={() => setCurrentPath('')}
            className="hover:text-editor-accent"
          >
            root
          </button>
          {currentPath.split('/').filter(Boolean).map((part, idx, arr) => (
            <span key={idx} className="flex items-center gap-1">
              <span className="text-editor-muted">/</span>
              <button
                onClick={() => setCurrentPath(arr.slice(0, idx + 1).join('/'))}
                className="hover:text-editor-accent"
              >
                {part}
              </button>
            </span>
          ))}
        </div>
      )}

      {/* File List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {isLoadingFiles ? (
          <div className="p-3 text-sm text-editor-muted">Loading...</div>
        ) : files.length === 0 ? (
          <div className="p-3 text-sm text-editor-muted">
            No files in workspace
          </div>
        ) : (
          <div className="py-1">
            {/* Back button if in subdirectory */}
            {currentPath && (
              <FileTreeItem
                file={{ name: '..', path: '..', is_directory: true }}
                isSelected={false}
                isExpanded={false}
                onClick={() => {
                  const parentPath = currentPath.split('/').slice(0, -1).join('/');
                  setCurrentPath(parentPath);
                }}
              />
            )}
            {/* Files sorted: directories first, then by name */}
            {[...files]
              .sort((a, b) => {
                if (a.is_directory && !b.is_directory) return -1;
                if (!a.is_directory && b.is_directory) return 1;
                return a.name.localeCompare(b.name);
              })
              .map((file) => (
                <FileTreeItem
                  key={file.path}
                  file={file}
                  isSelected={currentFile?.path === file.path}
                  isExpanded={expandedPaths.has(file.path)}
                  onClick={() => toggleExpand(file.path, file.is_directory)}
                />
              ))
            }
          </div>
        )}
      </div>
    </div>
  );
}

interface FileTreeItemProps {
  file: FileInfo;
  isSelected: boolean;
  isExpanded: boolean;
  onClick: () => void;
  depth?: number;
}

function FileTreeItem({ 
  file, 
  isSelected, 
  isExpanded, 
  onClick, 
  depth = 0 
}: FileTreeItemProps) {
  return (
    <div
      onClick={onClick}
      className={`
        flex items-center gap-1 px-2 py-1 cursor-pointer text-sm
        hover:bg-editor-bg transition-colors
        ${isSelected ? 'bg-editor-accent/20 text-editor-accent' : ''}
      `}
      style={{ paddingLeft: `${8 + depth * 12}px` }}
    >
      {file.is_directory ? (
        <>
          {isExpanded ? (
            <ChevronDown size={14} className="text-editor-muted" />
          ) : (
            <ChevronRight size={14} className="text-editor-muted" />
          )}
          {isExpanded ? (
            <FolderOpen size={14} className="text-editor-warning" />
          ) : (
            <Folder size={14} className="text-editor-warning" />
          )}
        </>
      ) : (
        <>
          <span className="w-3.5" />
          {getFileIcon(file.name)}
        </>
      )}
      <span className="truncate">{file.name}</span>
      {file.size !== undefined && !file.is_directory && (
        <span className="ml-auto text-xs text-editor-muted">
          {formatFileSize(file.size)}
        </span>
      )}
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

