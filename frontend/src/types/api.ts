/**
 * API相关类型定义
 * 与Backend API Gateway接口对应
 */

import { ApiResponse, PaginatedResponse, PaginationParams } from './common';

// API配置类型
export interface ApiConfig {
  baseURL: string;
  timeout: number;
  headers?: Record<string, string>;
}

// 请求配置类型
export interface RequestConfig {
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  data?: any;
  params?: any;
  headers?: Record<string, string>;
  timeout?: number;
}

// 认证相关API类型
export namespace AuthAPI {
  // 登录请求
  export interface LoginRequest {
    email: string;
    password: string;
  }

  // 登录响应（前端使用的格式）
  export interface LoginResponse {
    user: {
      id: string;
      email: string;
      name: string;
      role: string;
      tenant_id: string;
      is_active: boolean;
      avatar?: string;
    };
    access_token: string;
    refresh_token: string;
    expires_in: number;
  }

  // 后端实际返回的登录响应格式
  export interface BackendLoginResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    refresh_token: string;
    user_info: {
      user_id: string;
      email: string;
      tenant_id: string;
      role: string;
      is_active: boolean;
      last_login_at?: string;
      // 注意：后端还包含hashed_password，但前端不应该使用
    };
  }

  // 刷新令牌请求
  export interface RefreshTokenRequest {
    refresh_token: string;
  }

  // 刷新令牌响应
  export interface RefreshTokenResponse {
    access_token: string;
    expires_in: number;
  }

  // 登出请求
  export interface LogoutRequest {
    refresh_token?: string;
  }
}

// 租户管理API类型
export namespace TenantAPI {
  // 租户信息
  export interface Tenant {
    id: string;
    name: string;
    slug: string;
    description?: string;
    domain?: string;
    logo_url?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    
    // 统计信息
    stats?: {
      user_count: number;
      active_users: number;
      api_calls_today: number;
      storage_used: number;
    };
  }

  // 创建租户请求
  export interface CreateTenantRequest {
    name: string;
    slug: string;
    description?: string;
    domain?: string;
  }

  // 更新租户请求
  export interface UpdateTenantRequest {
    name?: string;
    description?: string;
    domain?: string;
    is_active?: boolean;
  }

  // 租户列表响应
  export type TenantsResponse = ApiResponse<PaginatedResponse<Tenant>>;

  // 租户详情响应
  export type TenantResponse = ApiResponse<Tenant>;
}

// 用户管理API类型
export namespace UserAPI {
  // 用户信息
  export interface User {
    id: string;
    email: string;
    name: string;
    username?: string;
    avatar?: string;
    phone?: string;
    role: string;
    tenant_id: string;
    is_active: boolean;
    is_verified: boolean;
    last_login_at?: string;
    created_at: string;
    updated_at: string;
  }

  // 创建用户请求
  export interface CreateUserRequest {
    email: string;
    name: string;
    username?: string;
    password: string;
    role: string;
    phone?: string;
  }

  // 更新用户请求
  export interface UpdateUserRequest {
    name?: string;
    username?: string;
    phone?: string;
    role?: string;
    is_active?: boolean;
  }

  // 用户列表响应
  export type UsersResponse = ApiResponse<PaginatedResponse<User>>;

  // 用户详情响应
  export type UserResponse = ApiResponse<User>;
}

// 供应商凭证API类型
export namespace SupplierAPI {
  // 供应商凭证
  export interface SupplierCredential {
    id: string;
    tenant_id: string;
    provider: string;
    name: string;
    api_key_preview?: string; // 脱敏显示
    api_endpoint?: string;
    model_config?: Record<string, any>;
    is_active: boolean;
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
  }

  // 更新供应商凭证请求
  export interface UpdateSupplierCredentialRequest {
    name?: string;
    api_key?: string;
    api_endpoint?: string;
    model_config?: Record<string, any>;
    is_active?: boolean;
  }

  // 供应商凭证列表响应
  export type SupplierCredentialsResponse = ApiResponse<PaginatedResponse<SupplierCredential>>;

  // 供应商凭证详情响应
  export type SupplierCredentialResponse = ApiResponse<SupplierCredential>;
}

// 健康检查API类型
export namespace HealthAPI {
  // 健康状态
  export interface HealthStatus {
    status: 'healthy' | 'unhealthy' | 'degraded';
    timestamp: string;
    version: string;
    uptime: number;
    
    // 服务状态
    services?: {
      [serviceName: string]: {
        status: 'healthy' | 'unhealthy';
        response_time_ms?: number;
        error?: string;
      };
    };
  }

  // 健康检查响应
  export type HealthResponse = ApiResponse<HealthStatus>;
}