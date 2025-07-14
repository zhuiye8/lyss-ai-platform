/**
 * 供应商凭证相关类型定义
 */

import { ID } from './common';

// 供应商凭证
export interface SupplierCredential {
  id: ID;
  tenant_id: ID;
  provider: string;
  name: string;
  api_key_preview?: string; // 脱敏显示
  api_key_full?: string; // 完整密钥（仅在需要时获取）
  api_key?: string; // 完整密钥（用于后端交互）
  api_endpoint?: string;
  model_config?: Record<string, any>;
  is_active: boolean;
  is_default?: boolean;
  connection_status?: 'connected' | 'disconnected' | 'error';
  last_tested_at?: string;
  created_at: string;
  updated_at: string;
}

// 创建供应商凭证请求
export interface CreateSupplierCredentialRequest {
  provider: string;
  name: string;
  api_key: string;
  api_endpoint?: string;
  model_config?: Record<string, any>;
  is_active?: boolean;
}

// 更新供应商凭证请求
export interface UpdateSupplierCredentialRequest {
  name?: string;
  api_key?: string;
  api_endpoint?: string;
  model_config?: Record<string, any>;
  is_active?: boolean;
}

// 供应商类型枚举
export type SupplierProvider = 
  | 'openai'
  | 'anthropic'
  | 'google'
  | 'azure'
  | 'baidu'
  | 'alibaba'
  | 'custom';

// 供应商配置
export interface SupplierConfig {
  name: string;
  icon: string;
  color: string;
  default_endpoint?: string;
  supported_models?: string[];
  required_fields?: string[];
  optional_fields?: string[];
}

// 连接测试结果
export interface ConnectionTestResult {
  success: boolean;
  response_time_ms?: number;
  error_message?: string;
  model_info?: {
    available_models: string[];
    default_model: string;
  };
  usage_info?: {
    quota_remaining?: number;
    requests_per_minute?: number;
  };
}

// 供应商统计信息
export interface SupplierStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time: number;
  total_tokens_used: number;
  cost_usd: number;
  last_request_at?: string;
}

// 供应商使用历史
export interface SupplierUsageHistory {
  id: ID;
  supplier_credential_id: ID;
  request_type: 'chat' | 'completion' | 'embedding' | 'image' | 'audio';
  model: string;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  cost_usd?: number;
  response_time_ms: number;
  status: 'success' | 'error' | 'timeout';
  error_message?: string;
  created_at: string;
}

// 模型信息
export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  type: 'chat' | 'completion' | 'embedding' | 'image' | 'audio';
  context_length: number;
  input_cost_per_token?: number;
  output_cost_per_token?: number;
  description?: string;
  deprecated?: boolean;
}

// 供应商限制信息
export interface SupplierLimits {
  requests_per_minute?: number;
  requests_per_day?: number;
  tokens_per_minute?: number;
  tokens_per_day?: number;
  concurrent_requests?: number;
}