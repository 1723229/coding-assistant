/**
 * BranchManager - 分支管理组件
 */

import { useState } from 'react';
import { GitBranch, Plus, Check, Loader2 } from 'lucide-react';

interface BranchManagerProps {
  sessionId: string;
  currentBranch: string;
  branches: string[];
  onCreateBranch: (name: string, checkout: boolean) => Promise<void>;
  onCheckout: (branch: string) => Promise<void>;
  isLoading: boolean;
}

export function BranchManager({ 
  currentBranch, 
  branches, 
  onCreateBranch, 
  onCheckout, 
  isLoading 
}: BranchManagerProps) {
  const [newBranchName, setNewBranchName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async () => {
    if (!newBranchName.trim()) return;
    
    setIsCreating(true);
    try {
      await onCreateBranch(newBranchName, true);
      setNewBranchName('');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Create Branch */}
      <div className="p-3 border-b border-editor-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={newBranchName}
            onChange={(e) => setNewBranchName(e.target.value)}
            placeholder="新分支名称"
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            className="flex-1 px-2 py-1.5 text-xs bg-editor-bg border border-editor-border rounded focus:outline-none focus:border-editor-accent"
          />
          <button
            onClick={handleCreate}
            disabled={isCreating || !newBranchName.trim() || isLoading}
            className="px-2 py-1.5 text-xs bg-editor-accent text-editor-panel rounded disabled:opacity-50 flex items-center gap-1"
          >
            {isCreating ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          </button>
        </div>
      </div>

      {/* Branch List */}
      <div className="flex-1 overflow-y-auto">
        {branches.length === 0 ? (
          <div className="text-center text-editor-muted text-xs py-8">
            暂无分支
          </div>
        ) : (
          branches.map((branch) => (
            <button
              key={branch}
              onClick={() => branch !== currentBranch && onCheckout(branch)}
              disabled={isLoading}
              className={`
                w-full px-3 py-2 text-xs text-left flex items-center gap-2
                border-b border-editor-border transition-colors
                ${branch === currentBranch 
                  ? 'bg-editor-accent/20 text-editor-accent' 
                  : 'hover:bg-editor-bg'
                }
                disabled:opacity-50
              `}
            >
              <GitBranch size={12} />
              <span className="flex-1 truncate">{branch}</span>
              {branch === currentBranch && (
                <Check size={12} className="flex-shrink-0" />
              )}
            </button>
          ))
        )}
      </div>
    </div>
  );
}

