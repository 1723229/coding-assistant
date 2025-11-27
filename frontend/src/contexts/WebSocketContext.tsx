/**
 * SSE Context - 全局状态管理（使用Server-Sent Events）
 */

import { createContext, useContext, useState, ReactNode } from 'react';
import { sseManager } from '../lib/sse';

interface SSEContextValue {
    isConnected: boolean;
    currentSessionId: string | null;
    connect: (sessionId: string) => void;
    disconnect: () => void;
    send: (content: string) => Promise<boolean>;
    interrupt: () => void;
}

const SSEContext = createContext<SSEContextValue | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
    const [isConnected, setIsConnected] = useState(false);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

    const connect = (sessionId: string) => {
        if (currentSessionId !== sessionId) {
            if (currentSessionId) {
                sseManager.disconnect(currentSessionId);
            }
            setCurrentSessionId(sessionId);
            // SSE不需要预先建立连接，有session就视为可连接
            setIsConnected(true);
        }
    };

    const disconnect = () => {
        if (currentSessionId) {
            sseManager.disconnect(currentSessionId);
            setCurrentSessionId(null);
            setIsConnected(false);
        }
    };

    const send = async (content: string): Promise<boolean> => {
        if (!currentSessionId) return false;

        // 发送时设置为processing状态
        setIsConnected(true);

        // 注册一次性的连接和断开处理器
        const handleConnect = () => {
            console.log('[SSE] Connected');
        };

        const handleDisconnect = () => {
            console.log('[SSE] Disconnected');
            // 断开后恢复可用状态（SSE是请求驱动的）
            setIsConnected(true);
        };

        const unsubConnect = sseManager.onConnect(currentSessionId, handleConnect);
        const unsubDisconnect = sseManager.onDisconnect(currentSessionId, handleDisconnect);

        try {
            const result = await sseManager.send(currentSessionId, content);
            return result;
        } finally {
            // 清理处理器
            unsubConnect();
            unsubDisconnect();
        }
    };

    const interrupt = () => {
        if (currentSessionId) {
            sseManager.interrupt(currentSessionId);
        }
    };

    return (
        <SSEContext.Provider
            value={{
                isConnected,
                currentSessionId,
                connect,
                disconnect,
                send,
                interrupt,
            }}
        >
            {children}
        </SSEContext.Provider>
    );
}

export function useWebSocketContext() {
    const context = useContext(SSEContext);
    if (!context) {
        throw new Error('useWebSocketContext must be used within WebSocketProvider');
    }
    return context;
}

