/**
 * RepoInfo - 仓库信息组件
 */

import { Github, Download } from 'lucide-react';

interface RepoInfoProps {
    repoUrl: string;
    branch: string;
    onPull: () => Promise<void>;
    isLoading: boolean;
}

export function RepoInfo({ repoUrl, branch, onPull, isLoading }: RepoInfoProps) {
    // Extract repo name from URL
    const repoName = repoUrl.split('/').slice(-2).join('/').replace('.git', '');

    return (
        <div className="p-3 space-y-3">
            {/* Repo Info */}
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <Github size={14} className="text-editor-muted" />
                    <span className="text-xs font-medium">仓库</span>
                </div>
                <div className="text-xs text-editor-muted truncate" title={repoUrl}>
                    {repoName}
                </div>
                <div className="text-xs text-editor-muted">
                    <span className="font-medium">分支:</span> {branch}
                </div>
            </div>

            {/* Actions - Only Pull, Push is in Changes tab */}
            <div>
                <button
                    onClick={onPull}
                    disabled={isLoading}
                    className="w-full px-2 py-1.5 text-xs bg-editor-bg border border-editor-border rounded flex items-center justify-center gap-1 hover:bg-editor-border disabled:opacity-50 transition-colors"
                >
                    <Download size={12} />
                    拉取最新代码 (Pull)
                </button>
                <p className="text-xs text-editor-muted mt-2 text-center">
                    提交和推送请前往「变更」标签页
                </p>
            </div>
        </div>
    );
}

