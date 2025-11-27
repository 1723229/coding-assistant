/**
 * SSE (Server-Sent Events) 管理器 - 单例模式
 */

import type { ChatMessage } from '../types';

type MessageHandler = (msg: ChatMessage) => void;
type ConnectionHandler = () => void;

const API_BASE = '/api/code';

class SSEManager {
  private eventSources: Map<string, EventSource> = new Map();
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private connectHandlers: Map<string, Set<ConnectionHandler>> = new Map();
  private disconnectHandlers: Map<string, Set<ConnectionHandler>> = new Map();
  private abortControllers: Map<string, AbortController> = new Map();

  async connect(sessionId: string, content: string): Promise<void> {
    // 关闭已存在的连接
    this.disconnect(sessionId);

    // 创建新的AbortController用于中断
    const abortController = new AbortController();
    this.abortControllers.set(sessionId, abortController);

    console.log('[SSE] Starting connection for session:', sessionId);

    try {
      // 使用fetch发起SSE请求
      const response = await fetch(`${API_BASE}/chat/stream/${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ content }),
        signal: abortController.signal,
      });

      console.log('[SSE] Response received, status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // 通知连接成功
      console.log('[SSE] Connection established, starting to read stream');
      this.connectHandlers.get(sessionId)?.forEach(h => h());

      // 读取流
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('[SSE] Stream completed');
          break;
        }

        // 解码并添加到缓冲区
        buffer += decoder.decode(value, { stream: true });

        // 处理完整的SSE消息
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留不完整的行

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // 移除 "data: " 前缀
            try {
              const message = JSON.parse(data);
              console.log('[SSE] Message received:', message.type);
              this.messageHandlers.get(sessionId)?.forEach(h => h(message));
            } catch (e) {
              console.error('[SSE] Failed to parse message:', data, e);
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('[SSE] Connection aborted');
      } else {
        console.error('[SSE] Connection error:', error);
        // 发送错误消息给handlers
        this.messageHandlers.get(sessionId)?.forEach(h =>
          h({ type: 'error', content: error.message } as ChatMessage)
        );
      }
    } finally {
      // 清理
      this.abortControllers.delete(sessionId);
      this.disconnectHandlers.get(sessionId)?.forEach(h => h());
      console.log('[SSE] Connection closed');
    }
  }

  disconnect(sessionId: string): void {
    // 中断fetch请求
    const controller = this.abortControllers.get(sessionId);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(sessionId);
    }
  }

  async send(sessionId: string, content: string): Promise<boolean> {
    try {
      await this.connect(sessionId, content);
      return true;
    } catch (error) {
      console.error('[SSE] Failed to send:', error);
      return false;
    }
  }

  async interrupt(sessionId: string): Promise<void> {
    try {
      // 调用中断API
      await fetch(`${API_BASE}/chat/interrupt/${sessionId}`, {
        method: 'POST',
      });

      // 断开当前连接
      this.disconnect(sessionId);
    } catch (error) {
      console.error('[SSE] Failed to interrupt:', error);
    }
  }

  isConnected(sessionId: string): boolean {
    return this.abortControllers.has(sessionId);
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

export const sseManager = new SSEManager();
