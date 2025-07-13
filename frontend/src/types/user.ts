/**
 * 用户相关类型定义
 */

import { Role, Status, ID } from './common';

// 用户基本信息
export interface User {
  id: ID;
  email: string;
  name: string;
  username?: string;
  avatar?: string;
  phone?: string;
  role: Role;
  tenant_id: ID;
  is_active: boolean;
  is_verified: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

// 用户偏好设置
export interface UserPreferences {
  id: ID;
  user_id: ID;
  tenant_id: ID;
  active_memory_enabled: boolean;
  preferred_language: 'zh' | 'en';
  theme_mode: 'light' | 'dark';
  notification_settings: {
    email_notifications: boolean;
    system_notifications: boolean;
    marketing_emails: boolean;
  };
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// 用户会话信息
export interface UserSession {
  user: User;
  token: {
    access_token: string;
    refresh_token: string;
    expires_in: number;
    token_type: 'Bearer';
  };
  permissions: string[];
  tenant: {
    id: ID;
    name: string;
    slug: string;
  };
}

// 登录凭据
export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

// 注册信息
export interface RegisterData {
  email: string;
  name: string;
  username?: string;
  password: string;
  confirm_password: string;
  phone?: string;
  agree_terms: boolean;
}

// 用户资料更新
export interface UserProfileUpdate {
  name?: string;
  username?: string;
  phone?: string;
  avatar?: string;
}

// 密码修改
export interface PasswordChange {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

// 用户统计信息
export interface UserStats {
  total_conversations: number;
  total_messages: number;
  api_calls_today: number;
  api_calls_month: number;
  storage_used: number;
  last_active: string;
}

// 用户活动日志
export interface UserActivity {
  id: ID;
  user_id: ID;
  action: string;
  resource_type?: string;
  resource_id?: string;
  ip_address: string;
  user_agent: string;
  metadata?: Record<string, any>;
  created_at: string;
}

// 用户角色定义
export interface UserRole {
  id: ID;
  name: string;
  display_name: string;
  description?: string;
  permissions: string[];
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// 用户权限
export interface UserPermission {
  id: ID;
  name: string;
  display_name: string;
  description?: string;
  resource: string;
  action: string;
  created_at: string;
}

// 创建用户请求
export interface CreateUserRequest {
  email: string;
  name: string;
  username?: string;
  password: string;
  role: string;
  phone?: string;
  is_active?: boolean;
}

// 更新用户请求
export interface UpdateUserRequest {
  name?: string;
  username?: string;
  email?: string;
  phone?: string;
  role?: string;
  is_active?: boolean;
}

// 用户邀请
export interface UserInvitation {
  id: ID;
  email: string;
  role: Role;
  tenant_id: ID;
  invited_by: ID;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  expires_at: string;
  created_at: string;
  updated_at: string;
}