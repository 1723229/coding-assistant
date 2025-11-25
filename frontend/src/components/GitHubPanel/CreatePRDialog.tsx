/**
 * CreatePRDialog - Pull Request 创建对话框
 */

import { useState } from 'react';
import { X, GitPullRequest, Loader2 } from 'lucide-react';

interface CreatePRDialogProps {
  sessionId: string;
  currentBranch: string;
  branches: string[];
  onClose: () => void;
  onCreate: (title: string, body: string, headBranch: string, baseBranch: string) => Promise<void>;
}

export function CreatePRDialog({ 
  sessionId, 
  currentBranch, 
  branches, 
  onClose, 
  onCreate 
}: CreatePRDialogProps) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [headBranch, setHeadBranch] = useState(currentBranch);
  const [baseBranch, setBaseBranch] = useState('main');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!title.trim()) {
      setError('标题不能为空');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      await onCreate(title, body, headBranch, baseBranch);
      onClose();
    } catch (err) {
      console.error('Failed to create PR:', err);
      setError(err instanceof Error ? err.message : 'Failed to create pull request');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-editor-panel border border-editor-border rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-editor-border">
          <div className="flex items-center gap-2">
            <GitPullRequest size={18} />
            <h2 className="text-base font-semibold">创建 Pull Request</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-editor-border transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {error && (
            <div className="p-3 bg-editor-error/20 text-editor-error text-sm rounded">
              {error}
            </div>
          )}

          {/* Branches */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-editor-muted mb-2">
                源分支 (Head)
              </label>
              <select
                value={headBranch}
                onChange={(e) => setHeadBranch(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-editor-bg border border-editor-border rounded focus:outline-none focus:border-editor-accent"
              >
                {branches.map((branch) => (
                  <option key={branch} value={branch}>
                    {branch}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-editor-muted mb-2">
                目标分支 (Base)
              </label>
              <select
                value={baseBranch}
                onChange={(e) => setBaseBranch(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-editor-bg border border-editor-border rounded focus:outline-none focus:border-editor-accent"
              >
                {branches
                  .filter((branch) => branch !== headBranch)
                  .map((branch) => (
                    <option key={branch} value={branch}>
                      {branch}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm text-editor-muted mb-2">
              标题 *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="简要描述这个 Pull Request"
              className="w-full px-3 py-2 text-sm bg-editor-bg border border-editor-border rounded focus:outline-none focus:border-editor-accent"
              autoFocus
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm text-editor-muted mb-2">
              描述
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="详细描述这个 Pull Request 的改动内容..."
              rows={8}
              className="w-full px-3 py-2 text-sm bg-editor-bg border border-editor-border rounded resize-none focus:outline-none focus:border-editor-accent"
            />
          </div>

          {/* Help Text */}
          <div className="text-xs text-editor-muted p-3 bg-editor-bg rounded">
            <p>💡 提示：</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>使用清晰简洁的标题描述改动</li>
              <li>在描述中说明改动的原因和影响</li>
              <li>可以使用 Markdown 格式编写描述</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-editor-border flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm border border-editor-border rounded hover:bg-editor-border transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleCreate}
            disabled={isLoading || !title.trim()}
            className="flex-1 px-4 py-2 text-sm bg-editor-accent text-editor-panel rounded hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <GitPullRequest size={16} />
                创建 Pull Request
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

