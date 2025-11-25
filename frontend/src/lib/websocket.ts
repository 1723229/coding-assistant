/**
 * WebSocket 管理器 - 单例模式
 */

import type { ChatMessage } from '../types';

type MessageHandler = (msg: ChatMessage) => void;
type ConnectionHandler = () => void;

class WebSocketManager {
  private connections: Map<string, WebSocket> = new Map();
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private connectHandlers: Map<string, Set<ConnectionHandler>> = new Map();
  private disconnectHandlers: Map<string, Set<ConnectionHandler>> = new Map();

  connect(sessionId: string): void {
    if (this.isConnected(sessionId)) {
      return;
    }

    const existingWs = this.connections.get(sessionId);
    if (existingWs) {
      existingWs.close();
      this.connections.delete(sessionId);
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/chat/ws/${sessionId}`);
    this.connections.set(sessionId, ws);

    ws.onopen = () => {
      this.connectHandlers.get(sessionId)?.forEach(h => h());
    };

    ws.onclose = () => {
      this.connections.delete(sessionId);
      this.disconnectHandlers.get(sessionId)?.forEach(h => h());
    };

    ws.onerror = () => {
      // Error handling
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.messageHandlers.get(sessionId)?.forEach(h => h(data));
      } catch {
        // Parse error - ignore malformed messages
      }
    };

    // Ping
    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      } else {
        clearInterval(ping);
      }
    }, 25000);
  }

  disconnect(sessionId: string): void {
    const ws = this.connections.get(sessionId);
    if (ws) {
      ws.close();
      this.connections.delete(sessionId);
    }
  }

  send(sessionId: string, content: string): boolean {
    const ws = this.connections.get(sessionId);
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'message', content }));
      return true;
    }
    return false;
  }

  interrupt(sessionId: string): void {
    const ws = this.connections.get(sessionId);
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'interrupt' }));
    }
  }

  isConnected(sessionId: string): boolean {
    const ws = this.connections.get(sessionId);
    return ws?.readyState === WebSocket.OPEN;
  }

  onMessage(sessionId: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(sessionId)) {
      this.messageHandlers.set(sessionId, new Set());
    }
    this.messageHandlers.get(sessionId)!.add(handler);
    return () => this.messageHandlers.get(sessionId)?.delete(handler);
  }

  onConnect(sessionId: string, handler: ConnectionHandler): () => void {
    if (!this.connectHandlers.has(sessionId)) {
      this.connectHandlers.set(sessionId, new Set());
    }
    this.connectHandlers.get(sessionId)!.add(handler);
    return () => this.connectHandlers.get(sessionId)?.delete(handler);
  }

  onDisconnect(sessionId: string, handler: ConnectionHandler): () => void {
    if (!this.disconnectHandlers.has(sessionId)) {
      this.disconnectHandlers.set(sessionId, new Set());
    }
    this.disconnectHandlers.get(sessionId)!.add(handler);
    return () => this.disconnectHandlers.get(sessionId)?.delete(handler);
  }
}

export const wsManager = new WebSocketManager();

