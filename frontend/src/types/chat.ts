/**
 * 聊天相关类型定义
 */

import { ID } from './common';

// 消息角色
export type MessageRole = 'user' | 'assistant' | 'system';

// 聊天消息
export interface ChatMessage {
  id: ID;
  conversation_id?: ID;
  content: string;
  role: MessageRole;
  model?: string;
  supplier?: string;
  tokens?: {
    input: number;
    output: number;
    total: number;
  };
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// 对话
export interface Conversation {
  id: ID;
  user_id: ID;
  tenant_id: ID;
  title: string;
  description?: string;
  model: string;
  supplier: string;
  config?: ChatConfig;
  message_count: number;
  total_tokens: number;
  cost_usd?: number;
  is_archived: boolean;
  is_shared: boolean;
  tags?: string[];
  created_at: string;
  updated_at: string;
  last_message_at?: string;
}

// 聊天配置
export interface ChatConfig {
  model: string;
  supplier: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stream: boolean;
  memory_enabled: boolean;
  system_prompt?: string;
  tools?: ChatTool[];
}

// 聊天工具
export interface ChatTool {
  type: 'function' | 'web_search' | 'code_interpreter' | 'file_retrieval';
  name: string;
  description: string;
  parameters?: Record<string, any>;
  enabled: boolean;
}

// 发送消息请求
export interface SendMessageRequest {
  message: string;
  conversation_id?: ID;
  model: string;
  supplier: string;
  config?: Partial<ChatConfig>;
  attachments?: MessageAttachment[];
}

// 流式聊天请求
export interface StreamChatRequest extends SendMessageRequest {
  // 继承所有SendMessageRequest字段
}

// 消息附件
export interface MessageAttachment {
  id: ID;
  type: 'image' | 'document' | 'audio' | 'video';
  filename: string;
  size: number;
  url: string;
  mime_type: string;
}

// 聊天响应
export interface ChatResponse {
  message_id: ID;
  conversation_id: ID;
  content: string;
  role: MessageRole;
  model: string;
  supplier: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  cost_usd?: number;
  execution_time_ms: number;
  metadata?: Record<string, any>;
}

// 流式聊天事件
export interface StreamChatEvent {
  type: 'start' | 'chunk' | 'end' | 'error';
  content?: string;
  delta?: string;
  execution_id?: string;
  conversation_id?: ID;
  message_id?: ID;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  error?: string;
}

// 对话搜索过滤器
export interface ConversationFilters {
  search?: string;
  model?: string;
  supplier?: string;
  tags?: string[];
  date_range?: {
    start_date: string;
    end_date: string;
  };
  is_archived?: boolean;
  is_shared?: boolean;
}

// 创建对话请求
export interface CreateConversationRequest {
  title?: string;
  description?: string;
  model: string;
  supplier: string;
  config?: Partial<ChatConfig>;
  tags?: string[];
}

// 更新对话请求
export interface UpdateConversationRequest {
  title?: string;
  description?: string;
  config?: Partial<ChatConfig>;
  tags?: string[];
  is_archived?: boolean;
  is_shared?: boolean;
}

// 对话统计
export interface ConversationStats {
  total_conversations: number;
  total_messages: number;
  total_tokens: number;
  total_cost_usd: number;
  average_messages_per_conversation: number;
  most_used_models: Array<{
    model: string;
    count: number;
    percentage: number;
  }>;
  daily_usage: Array<{
    date: string;
    message_count: number;
    token_count: number;
    cost_usd: number;
  }>;
}

// 聊天模板
export interface ChatTemplate {
  id: ID;
  name: string;
  description: string;
  prompt: string;
  config: ChatConfig;
  category: string;
  tags: string[];
  is_public: boolean;
  is_system: boolean;
  usage_count: number;
  created_by: ID;
  created_at: string;
  updated_at: string;
}

// 预设提示词
export interface PromptPreset {
  id: ID;
  title: string;
  content: string;
  category: string;
  tags: string[];
  usage_count: number;
  is_favorite: boolean;
  created_at: string;
}

// 聊天会话信息
export interface ChatSession {
  id: ID;
  user_id: ID;
  conversation_id?: ID;
  model: string;
  supplier: string;
  config: ChatConfig;
  status: 'active' | 'completed' | 'error';
  start_time: string;
  end_time?: string;
  message_count: number;
  total_tokens: number;
  cost_usd: number;
}