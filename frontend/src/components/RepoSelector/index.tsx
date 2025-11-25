/**
 * RepoSelector - 仓库搜索选择器
 * 参照用户截图实现，支持搜索和选择GitHub仓库
 */

import { useState, useEffect, useRef } from 'react';
import { Search, Check, Loader2 } from 'lucide-react';
import { githubApi } from '../../services/api';
import type { RepoInfo } from '../../types';

interface RepoSelectorProps {
  onSelect: (repo: RepoInfo) => void;
  onClose: () => void;
  selectedRepo?: RepoInfo | null;
}

export function RepoSelector({ onSelect, onClose, selectedRepo }: RepoSelectorProps) {
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [filteredRepos, setFilteredRepos] = useState<RepoInfo[]>([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadRepos();
    // Auto-focus search input
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    // Filter repos based on query
    if (!query.trim()) {
      setFilteredRepos(repos);
    } else {
      const q = query.toLowerCase();
      setFilteredRepos(
        repos.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            r.full_name.toLowerCase().includes(q) ||
            (r.description && r.description.toLowerCase().includes(q))
        )
      );
    }
    setSelectedIndex(0); // Reset selection when filtering
  }, [query, repos]);

  const loadRepos = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await githubApi.listUserRepos();
      setRepos(data);
      setFilteredRepos(data);
    } catch (err) {
      console.error('Failed to load repos:', err);
      setError('Failed to load repositories. Please check your GitHub token.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (repo: RepoInfo) => {
    onSelect(repo);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, filteredRepos.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredRepos[selectedIndex]) {
        handleSelect(filteredRepos[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  // Auto-scroll selected item into view
  useEffect(() => {
    const selectedElement = listRef.current?.children[selectedIndex] as HTMLElement;
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-editor-panel border border-editor-border rounded-lg shadow-xl w-full max-w-2xl max-h-[70vh] flex flex-col">
        {/* Search Input */}
        <div className="p-4 border-b border-editor-border">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-editor-muted"
              size={18}
            />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="搜索仓库..."
              className="w-full pl-10 pr-4 py-2 text-sm bg-editor-bg border border-editor-border rounded focus:outline-none focus:border-editor-accent"
            />
          </div>
          {error && (
            <div className="mt-2 text-xs text-editor-error">{error}</div>
          )}
        </div>

        {/* Repos List */}
        <div ref={listRef} className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-editor-muted" size={32} />
            </div>
          ) : filteredRepos.length === 0 ? (
            <div className="text-center text-editor-muted text-sm py-12">
              {query ? '未找到匹配的仓库' : '暂无仓库'}
            </div>
          ) : (
            filteredRepos.map((repo, index) => {
              const isSelected = selectedIndex === index;
              const isCurrentlySelected = selectedRepo?.full_name === repo.full_name;
              
              return (
                <button
                  key={repo.full_name}
                  onClick={() => handleSelect(repo)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`
                    w-full text-left px-4 py-3 border-b border-editor-border
                    transition-colors relative
                    ${isSelected ? 'bg-editor-accent/20' : 'hover:bg-editor-bg'}
                  `}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium truncate">
                          {repo.full_name}
                        </span>
                        {repo.is_private && (
                          <span className="text-xs px-1.5 py-0.5 bg-editor-warning/20 text-editor-warning rounded">
                            Private
                          </span>
                        )}
                      </div>
                      {repo.description && (
                        <p className="text-xs text-editor-muted line-clamp-2">
                          {repo.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-editor-muted">
                          默认分支: {repo.default_branch}
                        </span>
                      </div>
                    </div>
                    {isCurrentlySelected && (
                      <Check size={18} className="text-editor-accent flex-shrink-0" />
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-editor-border text-xs text-editor-muted flex items-center justify-between">
          <div>
            <span className="font-mono">↑↓</span> 导航 ·{' '}
            <span className="font-mono">Enter</span> 选择 ·{' '}
            <span className="font-mono">Esc</span> 关闭
          </div>
          <div>
            {filteredRepos.length} 个仓库
          </div>
        </div>
      </div>
    </div>
  );
}

