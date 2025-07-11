/**
 * 通用类型定义
 * 根据STANDARDS.md中的API响应规范定义
 */

// API响应基础类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  request_id: string;
  timestamp: string;
  error?: ApiError;
}

// 错误信息类型
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// 分页信息类型
export interface PaginationInfo {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// 分页响应类型
export interface PaginatedResponse<T = any> {
  items: T[];
  pagination: PaginationInfo;
}

// 分页请求参数
export interface PaginationParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

// 表格列配置
export interface TableColumn {
  key: string;
  title: string;
  dataIndex?: string;
  width?: number | string;
  align?: 'left' | 'center' | 'right';
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: any, record: any, index: number) => React.ReactNode;
}

// 表单字段配置
export interface FormField {
  name: string;
  label: string;
  type: 'input' | 'password' | 'email' | 'select' | 'textarea' | 'switch' | 'number';
  required?: boolean;
  placeholder?: string;
  rules?: any[];
  options?: Array<{ label: string; value: any }>;
}

// 菜单项类型
export interface MenuItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  path?: string;
  children?: MenuItem[];
  permission?: string;
}

// 面包屑项
export interface BreadcrumbItem {
  title: string;
  path?: string;
}

// 加载状态类型
export interface LoadingState {
  loading: boolean;
  error?: string | null;
}

// 通用ID类型
export type ID = string;

// 通用状态类型
export type Status = 'active' | 'inactive' | 'pending' | 'disabled';

// 通用角色类型
export type Role = 'admin' | 'user' | 'viewer';

// 环境类型
export type Environment = 'development' | 'staging' | 'production';

// 主题类型
export type ThemeMode = 'light' | 'dark';

// 语言类型
export type Language = 'zh' | 'en';

// HTTP方法类型
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

// 排序方向
export type SortOrder = 'asc' | 'desc' | null;

// 响应式断点
export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'xxl';