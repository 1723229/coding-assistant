/**
 * Chat Panel - 优化事件展示版本
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Loader2, StopCircle, Wifi, WifiOff } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useSessionStore } from '../../hooks/useSession';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import { wsManager } from '../../lib/websocket';
import { EventMessage } from './EventMessage';
import type { ChatMessage, Message } from '../../types';

export function ChatPanel() {
    const { currentSession, messages, addMessage, appendToLastMessage } = useSessionStore();
    const { isConnected, connect, send, interrupt } = useWebSocketContext();
    const [input, setInput] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // 当 session 变化时，连接 WebSocket
    useEffect(() => {
        if (currentSession?.id) {
            connect(currentSession.id);

            // 注册消息处理
            const unsubscribe = wsManager.onMessage(currentSession.id, handleMessage);
            return () => unsubscribe();
        }
    }, [currentSession?.id, connect]);

    // 处理 WebSocket 消息
    const handleMessage = useCallback((msg: ChatMessage) => {
        const timestamp = new Date().toISOString();

        switch (msg.type) {
            case 'connected':
            case 'user_message_received':
            case 'pong':
                // 静默处理
                break;

            case 'text':
                addMessage({ role: 'assistant', content: msg.content });
                break;

            case 'text_delta':
                appendToLastMessage(msg.content);
                break;

            case 'thinking':
                addMessage({
                    role: 'assistant',
                    content: msg.content,
                    // @ts-ignore - 添加自定义属性用于EventMessage
                    eventType: 'thinking',
                    timestamp,
                    metadata: msg.metadata,
                });
                break;

            case 'tool_use':
                addMessage({
                    role: 'assistant',
                    content: msg.content || `Using tool: ${msg.tool_name}`,
                    tool_name: msg.tool_name,
                    // @ts-ignore - 添加自定义属性用于EventMessage
                    eventType: 'tool_use',
                    timestamp,
                    metadata: {
                        tool_name: msg.tool_name,
                        tool_input: msg.tool_input,
                        tool_use_id: msg.metadata?.tool_use_id,
                    },
                });
                break;

            case 'tool_result':
                addMessage({
                    role: 'system',
                    content: msg.content,
                    // @ts-ignore - 添加自定义属性用于EventMessage
                    eventType: 'tool_result',
                    timestamp,
                    metadata: {
                        tool_use_id: msg.metadata?.tool_use_id,
                    },
                });
                break;

            case 'system':
                addMessage({
                    role: 'system',
                    content: msg.content,
                    // @ts-ignore - 添加自定义属性用于EventMessage
                    eventType: 'system',
                    timestamp,
                    metadata: msg.metadata,
                });
                break;

            case 'result':
                addMessage({
                    role: 'system',
                    content: msg.content || 'Task completed',
                    // @ts-ignore - 添加自定义属性用于EventMessage
                    eventType: 'result',
                    timestamp,
                    metadata: msg.metadata,
                });
                setIsProcessing(false);
                break;

            case 'response_complete':
                setIsProcessing(false);
                break;

            case 'error':
                addMessage({
                    role: 'system',
                    content: msg.content || 'An error occurred',
                    // @ts-ignore - 添加自定义属性用于EventMessage
                    eventType: 'error',
                    timestamp,
                    metadata: { is_error: true, ...msg.metadata },
                });
                setIsProcessing(false);
                break;
        }
    }, [addMessage, appendToLastMessage]);

    // 自动滚动到底部
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const content = input.trim();

        if (!content || !isConnected || isProcessing) {
            return;
        }

        const userMessage: Message = { role: 'user', content };
        addMessage(userMessage);

        const sent = send(content);
        if (sent) {
            setInput('');
            setIsProcessing(true);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleInterrupt = () => {
        interrupt();
        setIsProcessing(false);
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-3 border-b border-editor-border flex items-center justify-between">
                <h3 className="font-semibold text-sm">Chat with Claude</h3>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-editor-muted">
                        {isConnected ? 'Connected' : 'Disconnected'}
                    </span>
                    {isConnected ? (
                        <Wifi size={14} className="text-editor-success" />
                    ) : (
                        <WifiOff size={14} className="text-editor-error" />
                    )}
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 space-y-4 scrollbar-thin">
                {messages.length === 0 ? (
                    <div className="text-center text-editor-muted text-sm py-8">
                        <p>Start a conversation with Claude</p>
                        <p className="text-xs mt-2">
                            Claude can help you write, edit, and understand code
                        </p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <MessageBubble key={idx} message={msg} />
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-editor-border">
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <div className="flex-1 relative">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={isConnected ? "Ask Claude..." : "Connecting..."}
                            disabled={!isConnected}
                            rows={2}
                            className="w-full px-3 py-2 text-sm bg-editor-bg border border-editor-border rounded-lg resize-none focus:outline-none focus:border-editor-accent disabled:opacity-50"
                        />
                    </div>
                    {isProcessing ? (
                        <button
                            type="button"
                            onClick={handleInterrupt}
                            className="p-2 bg-editor-error/20 text-editor-error rounded-lg hover:bg-editor-error/30 transition-colors self-end"
                            title="Stop"
                        >
                            <StopCircle size={20} />
                        </button>
                    ) : (
                        <button
                            type="submit"
                            disabled={!isConnected || !input.trim()}
                            className="p-2 bg-editor-accent text-editor-panel rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed self-end"
                            title="Send"
                        >
                            {isConnected ? <Send size={20} /> : <Loader2 size={20} className="animate-spin" />}
                        </button>
                    )}
                </form>
            </div>
        </div>
    );
}

function MessageBubble({ message }: { message: Message & { eventType?: string; timestamp?: string; metadata?: any } }) {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';
    const isEvent = message.eventType && ['thinking', 'tool_use', 'tool_result', 'system', 'result', 'error'].includes(message.eventType);

    // 使用 EventMessage 组件展示事件类型消息
    if (isEvent && message.eventType !== 'system') {
        return <EventMessage message={message} />;
    }

    // 常规消息气泡
    return (
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div
                className={`
          max-w-[85%] rounded-lg px-3 py-2 text-sm
          ${isUser
                        ? 'bg-editor-accent text-editor-panel'
                        : isSystem
                            ? 'bg-editor-warning/20 text-editor-warning'
                            : 'bg-editor-bg border border-editor-border'
                    }
        `}
            >
                {isUser ? (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                ) : isSystem ? (
                    <EventMessage message={message} />
                ) : (
                    <div className="prose prose-sm prose-invert max-w-none">
                        <ReactMarkdown
                            components={{
                                code({ className, children, ...props }) {
                                    const match = /language-(\w+)/.exec(className || '');
                                    const isInline = !match;

                                    return isInline ? (
                                        <code className="bg-editor-panel px-1 py-0.5 rounded text-xs" {...props}>
                                            {children}
                                        </code>
                                    ) : (
                                        <SyntaxHighlighter
                                            style={oneDark}
                                            language={match[1]}
                                            PreTag="div"
                                            customStyle={{
                                                margin: 0,
                                                borderRadius: '0.375rem',
                                                fontSize: '0.75rem',
                                            }}
                                        >
                                            {String(children).replace(/\n$/, '')}
                                        </SyntaxHighlighter>
                                    );
                                },
                            }}
                        >
                            {message.content}
                        </ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    );
}
