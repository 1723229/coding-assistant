/**
 * WebSocket Context - 全局状态管理
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { wsManager } from '../lib/websocket';

interface WebSocketContextValue {
    isConnected: boolean;
    currentSessionId: string | null;
    connect: (sessionId: string) => void;
    disconnect: () => void;
    send: (content: string) => boolean;
    interrupt: () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
    const [isConnected, setIsConnected] = useState(false);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

    useEffect(() => {
        if (!currentSessionId) {
            setIsConnected(false);
            return;
        }

        // 初始状态
        setIsConnected(wsManager.isConnected(currentSessionId));

        // 监听连接
        const unsubConnect = wsManager.onConnect(currentSessionId, () => {
            setIsConnected(true);
        });

        // 监听断开
        const unsubDisconnect = wsManager.onDisconnect(currentSessionId, () => {
            setIsConnected(false);
        });

        // 建立连接
        wsManager.connect(currentSessionId);

        return () => {
            unsubConnect();
            unsubDisconnect();
        };
    }, [currentSessionId]);

    const connect = (sessionId: string) => {
        if (currentSessionId !== sessionId) {
            if (currentSessionId) {
                wsManager.disconnect(currentSessionId);
            }
            setCurrentSessionId(sessionId);
        }
    };

    const disconnect = () => {
        if (currentSessionId) {
            wsManager.disconnect(currentSessionId);
            setCurrentSessionId(null);
        }
    };

    const send = (content: string): boolean => {
        if (!currentSessionId) return false;
        return wsManager.send(currentSessionId, content);
    };

    const interrupt = () => {
        if (currentSessionId) {
            wsManager.interrupt(currentSessionId);
        }
    };

    return (
        <WebSocketContext.Provider
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
        </WebSocketContext.Provider>
    );
}

export function useWebSocketContext() {
    const context = useContext(WebSocketContext);
    if (!context) {
        throw new Error('useWebSocketContext must be used within WebSocketProvider');
    }
    return context;
}

