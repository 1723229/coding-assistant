/**
 * GitHub Settings - 令牌管理组件
 * 参照用户提供的截图实现
 */

import { useState, useEffect } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import type { GitHubToken } from '../../types';

interface GitHubSettingsProps {
    onClose: () => void;
}

export function GitHubSettings({ onClose }: GitHubSettingsProps) {
    const [tokens, setTokens] = useState<GitHubToken[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showAddDialog, setShowAddDialog] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Add token form state
    const [platform, setPlatform] = useState<'GitHub' | 'GitLab'>('GitHub');
    const [domain, setDomain] = useState('github.com');
    const [token, setToken] = useState('');

    useEffect(() => {
        loadTokens();
    }, []);

    const loadTokens = async () => {
        try {
            setIsLoading(true);
            const response = await fetch('/api/github/tokens');
            if (response.ok) {
                const data = await response.json();
                setTokens(data);
            }
        } catch (err) {
            console.error('Failed to load tokens:', err);
            setError('Failed to load tokens');
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddToken = async () => {
        if (!token.trim()) {
            setError('Token cannot be empty');
            return;
        }

        try {
            setIsLoading(true);
            setError(null);

            const response = await fetch('/api/github/tokens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform, domain, token }),
            });

            if (response.ok) {
                await loadTokens();
                setShowAddDialog(false);
                setPlatform('GitHub');
                setDomain('github.com');
                setToken('');
            } else {
                const error = await response.json();
                setError(error.detail || 'Failed to add token');
            }
        } catch (err) {
            console.error('Failed to add token:', err);
            setError('Failed to add token');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeleteToken = async (tokenId: string) => {
        if (!confirm('确定要删除此令牌吗？')) return;

        try {
            setIsLoading(true);
            const response = await fetch(`/api/github/tokens/${tokenId}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                await loadTokens();
            }
        } catch (err) {
            console.error('Failed to delete token:', err);
            setError('Failed to delete token');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-editor-panel border border-editor-border rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-editor-border">
                    <h2 className="text-lg font-semibold">集成</h2>
                    <button
                        onClick={onClose}
                        className="p-1 rounded hover:bg-editor-border transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                    <p className="text-sm text-editor-muted mb-4">
                        设置外部服务以增强您的工作流程
                    </p>

                    {error && (
                        <div className="mb-4 p-3 bg-editor-error/20 text-editor-error text-sm rounded">
                            {error}
                        </div>
                    )}

                    {/* Tokens List */}
                    <div className="space-y-2 mb-4">
                        {tokens.length === 0 && !isLoading ? (
                            <div className="text-center text-editor-muted text-sm py-8">
                                暂无令牌，点击下方按钮添加
                            </div>
                        ) : (
                            tokens.map((t) => (
                                <div
                                    key={t.id}
                                    className="flex items-center gap-3 p-3 bg-editor-bg border border-editor-border rounded"
                                >
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-sm font-medium">{t.platform}</span>
                                            <span className="text-xs text-editor-muted font-mono">
                                                {t.domain}
                                            </span>
                                        </div>
                                        <div className="text-xs text-editor-muted font-mono truncate">
                                            {t.token}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDeleteToken(t.id)}
                                        className="p-2 rounded hover:bg-editor-error/20 hover:text-editor-error transition-colors"
                                        title="删除"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Add Token Button */}
                    {!showAddDialog && (
                        <button
                            onClick={() => setShowAddDialog(true)}
                            className="w-full px-4 py-2 bg-editor-accent text-editor-panel rounded flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
                        >
                            <Plus size={16} />
                            新增令牌
                        </button>
                    )}

                    {/* Add Token Dialog */}
                    {showAddDialog && (
                        <div className="space-y-4 p-4 bg-editor-bg border border-editor-border rounded">
                            <h3 className="font-medium text-sm">新增 Git 令牌</h3>

                            {/* Platform Selection */}
                            <div>
                                <label className="block text-sm text-editor-muted mb-2">
                                    平台
                                </label>
                                <div className="flex gap-4">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="platform"
                                            value="GitHub"
                                            checked={platform === 'GitHub'}
                                            onChange={(e) => {
                                                setPlatform(e.target.value as 'GitHub');
                                                setDomain('github.com');
                                            }}
                                            className="w-4 h-4"
                                        />
                                        <span className="text-sm">GitHub</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="platform"
                                            value="GitLab"
                                            checked={platform === 'GitLab'}
                                            onChange={(e) => {
                                                setPlatform(e.target.value as 'GitLab');
                                                setDomain('gitlab.com');
                                            }}
                                            className="w-4 h-4"
                                        />
                                        <span className="text-sm">GitLab</span>
                                    </label>
                                </div>
                            </div>

                            {/* Domain Input */}
                            <div>
                                <label className="block text-sm text-editor-muted mb-2">
                                    平台域名
                                </label>
                                <input
                                    type="text"
                                    value={domain}
                                    onChange={(e) => setDomain(e.target.value)}
                                    placeholder="github.com"
                                    className="w-full px-3 py-2 text-sm bg-editor-panel border border-editor-border rounded focus:outline-none focus:border-editor-accent"
                                />
                            </div>

                            {/* Token Input */}
                            <div>
                                <label className="block text-sm text-editor-muted mb-2">
                                    个人访问令牌
                                </label>
                                <input
                                    type="password"
                                    value={token}
                                    onChange={(e) => setToken(e.target.value)}
                                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                                    className="w-full px-3 py-2 text-sm bg-editor-panel border border-editor-border rounded focus:outline-none focus:border-editor-accent font-mono"
                                />
                            </div>

                            {/* Help Text */}
                            <div className="text-xs text-editor-muted space-y-1 p-3 bg-editor-panel rounded">
                                <p className="font-medium">如何获取 {platform} 令牌：</p>
                                {platform === 'GitHub' && (
                                    <>
                                        <p>1. 访问 <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="text-editor-accent hover:underline">https://github.com/settings/tokens</a></p>
                                        <p>2. 点击 "Generate new token (classic)"</p>
                                        <p>3. 选择合适的权限范围并复制生成的令牌</p>
                                    </>
                                )}
                                {platform === 'GitLab' && (
                                    <>
                                        <p>1. 访问 GitLab 用户设置 → Access Tokens</p>
                                        <p>2. 创建新的个人访问令牌</p>
                                        <p>3. 选择合适的权限范围并复制生成的令牌</p>
                                    </>
                                )}
                            </div>

                            {/* Actions */}
                            <div className="flex gap-2">
                                <button
                                    onClick={() => {
                                        setShowAddDialog(false);
                                        setError(null);
                                        setToken('');
                                    }}
                                    className="flex-1 px-4 py-2 text-sm border border-editor-border rounded hover:bg-editor-border transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleAddToken}
                                    disabled={isLoading || !token.trim()}
                                    className="flex-1 px-4 py-2 text-sm bg-editor-accent text-editor-panel rounded hover:opacity-90 transition-opacity disabled:opacity-50"
                                >
                                    保存令牌
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

