/**
 * 租户相关类型定义
 */

import { Status, ID } from './common';

// 租户基本信息
export interface Tenant {
  id: ID;
  name: string;
  slug: string;
  description?: string;
  domain?: string;
  logo_url?: string;
  is_active: boolean;
  subscription_plan?: 'free' | 'basic' | 'premium' | 'enterprise';
  subscription_status?: 'active' | 'inactive' | 'suspended' | 'cancelled';
  created_at: string;
  updated_at: string;
  
  // 租户设置
  settings?: {
    max_users: number;
    max_storage: number; // 字节数
    max_api_calls_per_month: number;
    features: string[];
    custom_domain_enabled: boolean;
    sso_enabled: boolean;
  };
}

// 租户创建请求
export interface CreateTenantRequest {
  name: string;
  slug: string;
  description?: string;
  domain?: string;
  subscription_plan?: string;
}

// 租户更新请求
export interface UpdateTenantRequest {
  name?: string;
  description?: string;
  domain?: string;
  is_active?: boolean;
  settings?: Partial<Tenant['settings']>;
}

// 租户统计信息
export interface TenantStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  total_conversations: number;
  api_calls_today: number;
  api_calls_month: number;
  storage_used: number;
  storage_limit: number;
  
  // 时间序列数据
  daily_stats: Array<{
    date: string;
    api_calls: number;
    active_users: number;
    new_conversations: number;
  }>;
  
  // 最近活动
  recent_activities: Array<{
    timestamp: string;
    user_name: string;
    action: string;
    resource: string;
  }>;
}

// 租户配置
export interface TenantConfig {
  id: ID;
  tenant_id: ID;
  category: string;
  key: string;
  value: any;
  description?: string;
  is_encrypted: boolean;
  created_at: string;
  updated_at: string;
}

// 租户工具配置
export interface TenantToolConfig {
  id: ID;
  tenant_id: ID;
  tool_name: string;
  tool_config: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

// 租户API使用情况
export interface TenantApiUsage {
  tenant_id: ID;
  period: 'day' | 'week' | 'month' | 'year';
  start_date: string;
  end_date: string;
  
  // 总体使用量
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  
  // 按服务分类
  usage_by_service: Record<string, {
    requests: number;
    success_rate: number;
    avg_response_time: number;
  }>;
  
  // 按时间分布
  usage_timeline: Array<{
    timestamp: string;
    requests: number;
    response_time: number;
  }>;
}

// 租户计费信息
export interface TenantBilling {
  tenant_id: ID;
  billing_period: {
    start_date: string;
    end_date: string;
  };
  
  // 计费项目
  billing_items: Array<{
    service: string;
    usage: number;
    unit: string;
    unit_price: number;
    total_amount: number;
  }>;
  
  // 总计
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  
  // 支付状态
  payment_status: 'pending' | 'paid' | 'overdue' | 'failed';
  due_date: string;
}

// 租户订阅计划
export interface SubscriptionPlan {
  id: ID;
  name: string;
  display_name: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  
  // 计划限制
  limits: {
    max_users: number;
    max_storage: number;
    max_api_calls_per_month: number;
    max_projects: number;
  };
  
  // 功能特性
  features: Array<{
    name: string;
    description: string;
    enabled: boolean;
  }>;
  
  is_popular: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}