/**
 * EventMessage - 可折叠的事件展示组件
 * 用于展示工具调用、思考过程、系统事件等
 */

import { useState } from 'react';
import { 
  ChevronDown, 
  ChevronRight,
  Terminal, 
  Brain, 
  Wrench, 
  CheckCircle, 
  AlertCircle, 
  Info,
  Clock
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../../types';

// 事件类型配置
const EVENT_CONFIG = {
  thinking: { 
    icon: Brain, 
    color: 'text-purple-400', 
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
    label: '思考中' 
  },
  tool_use: { 
    icon: Wrench, 
    color: 'text-blue-400', 
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    label: '工具调用' 
  },
  tool_result: { 
    icon: Terminal, 
    color: 'text-green-400', 
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    label: '执行结果' 
  },
  system: { 
    icon: Info, 
    color: 'text-gray-400', 
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
    label: '系统' 
  },
  result: { 
    icon: CheckCircle, 
    color: 'text-green-500', 
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    label: '完成' 
  },
  error: { 
    icon: AlertCircle, 
    color: 'text-red-500', 
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    label: '错误' 
  }
};

interface EventMessageProps {
  message: Message & {
    eventType?: string;
    timestamp?: string;
    metadata?: {
      tool_name?: string;
      tool_input?: any;
      tool_use_id?: string;
      duration_ms?: number;
      is_error?: boolean;
    };
  };
}

export function EventMessage({ message }: EventMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const eventType = message.eventType || 'system';
  const config = EVENT_CONFIG[eventType as keyof typeof EVENT_CONFIG] || EVENT_CONFIG.system;
  const Icon = config.icon;
  
  const hasDetails = message.metadata?.tool_input || (message.content && message.content.length > 100);
  const toolName = message.metadata?.tool_name || message.tool_name;
  
  // 格式化工具输入
  const formatToolInput = (input: any): string => {
    if (typeof input === 'string') return input;
    try {
      return JSON.stringify(input, null, 2);
    } catch {
      return String(input);
    }
  };
  
  // 格式化时间戳
  const formatTime = (timestamp?: string): string => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };
  
  // 格式化持续时间
  const formatDuration = (ms?: number): string => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };
  
  return (
    <div className={`relative pl-8 pb-3 border-l-2 ${config.borderColor}`}>
      {/* 时间线图标 */}
      <div className={`absolute left-[-9px] top-0 p-1 rounded-full ${config.bgColor} ${config.color}`}>
        <Icon size={16} />
      </div>
      
      {/* 事件内容 */}
      <div className="flex-1">
        {/* 事件头部 */}
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-medium ${config.color}`}>
            {config.label}
          </span>
          
          {toolName && (
            <span className="text-xs text-editor-muted font-mono">
              {toolName}
            </span>
          )}
          
          {message.timestamp && (
            <span className="text-xs text-editor-muted flex items-center gap-1">
              <Clock size={10} />
              {formatTime(message.timestamp)}
            </span>
          )}
          
          {message.metadata?.duration_ms && (
            <span className="text-xs text-editor-muted">
              {formatDuration(message.metadata.duration_ms)}
            </span>
          )}
          
          {hasDetails && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="ml-auto p-0.5 rounded hover:bg-editor-border transition-colors"
              title={isExpanded ? '收起' : '展开'}
            >
              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
          )}
        </div>
        
        {/* 简要内容 */}
        {!isExpanded && (
          <div className="text-sm text-editor-text">
            {message.content.length > 100 
              ? `${message.content.substring(0, 100)}...` 
              : message.content
            }
          </div>
        )}
        
        {/* 详细内容（展开时） */}
        {isExpanded && (
          <div className="space-y-2 mt-2">
            {/* 完整内容 */}
            <div className="text-sm text-editor-text whitespace-pre-wrap">
              {message.content}
            </div>
            
            {/* 工具输入 */}
            {message.metadata?.tool_input && (
              <div className="space-y-1">
                <div className="text-xs text-editor-muted font-medium">输入参数:</div>
                <SyntaxHighlighter
                  language="json"
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    borderRadius: '0.375rem',
                    fontSize: '0.75rem',
                    padding: '0.5rem',
                  }}
                >
                  {formatToolInput(message.metadata.tool_input)}
                </SyntaxHighlighter>
              </div>
            )}
            
            {/* 工具使用ID（用于调试） */}
            {message.metadata?.tool_use_id && (
              <div className="text-xs text-editor-muted font-mono">
                ID: {message.metadata.tool_use_id}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

