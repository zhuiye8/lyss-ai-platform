/**
 * 应用常量定义
 */

// 应用配置
export const APP_CONFIG = {
  NAME: import.meta.env.VITE_APP_NAME || 'Lyss AI Platform',
  VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
  DESCRIPTION: '企业级AI服务聚合与管理平台',
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
} as const;

// 路由路径
export const ROUTES = {
  // 公共路由
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  
  // 认证后路由
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  SETTINGS: '/settings',
  
  // 管理路由
  ADMIN: '/admin',
  ADMIN_TENANTS: '/admin/tenants',
  ADMIN_USERS: '/admin/users',
  ADMIN_SUPPLIERS: '/admin/suppliers',
  ADMIN_ANALYTICS: '/admin/analytics',
  
  // AI功能路由
  CHAT: '/chat',
  CONVERSATIONS: '/conversations',
  MEMORY: '/memory',
  
  // 错误页面
  NOT_FOUND: '/404',
  UNAUTHORIZED: '/401',
  FORBIDDEN: '/403',
  ERROR: '/error',
} as const;

// API端点
export const API_ENDPOINTS = {
  // 认证相关
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    LOGOUT: '/api/v1/auth/logout',
    REFRESH: '/api/v1/auth/refresh',
    VERIFY: '/api/v1/auth/verify',
    ME: '/api/v1/auth/me',
    CHANGE_PASSWORD: '/api/v1/auth/change-password',
  },
  
  // 租户管理
  TENANTS: {
    LIST: '/api/v1/admin/tenants',
    CREATE: '/api/v1/admin/tenants',
    DETAIL: (id: string) => `/api/v1/admin/tenants/${id}`,
    UPDATE: (id: string) => `/api/v1/admin/tenants/${id}`,
    DELETE: (id: string) => `/api/v1/admin/tenants/${id}`,
    STATS: (id: string) => `/api/v1/admin/tenants/${id}/stats`,
  },
  
  // 用户管理
  USERS: {
    LIST: '/api/v1/admin/users',
    CREATE: '/api/v1/admin/users',
    DETAIL: (id: string) => `/api/v1/admin/users/${id}`,
    UPDATE: (id: string) => `/api/v1/admin/users/${id}`,
    DELETE: (id: string) => `/api/v1/admin/users/${id}`,
  },
  
  // 供应商凭证
  SUPPLIERS: {
    LIST: '/api/v1/admin/suppliers',
    CREATE: '/api/v1/admin/suppliers',
    DETAIL: (id: string) => `/api/v1/admin/suppliers/${id}`,
    UPDATE: (id: string) => `/api/v1/admin/suppliers/${id}`,
    DELETE: (id: string) => `/api/v1/admin/suppliers/${id}`,
  },
  
  // 健康检查
  HEALTH: '/health',
  HEALTH_SERVICES: '/health/services',
} as const;

// 本地存储键名
export const STORAGE_KEYS = {
  ACCESS_TOKEN: import.meta.env.VITE_JWT_STORAGE_KEY || 'lyss_access_token',
  REFRESH_TOKEN: import.meta.env.VITE_REFRESH_TOKEN_KEY || 'lyss_refresh_token',
  USER_PREFERENCES: 'lyss_user_preferences',
  THEME_MODE: 'lyss_theme_mode',
  LANGUAGE: 'lyss_language',
  SIDEBAR_COLLAPSED: 'lyss_sidebar_collapsed',
  RECENT_SEARCHES: 'lyss_recent_searches',
} as const;

// 分页配置
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: parseInt(import.meta.env.VITE_DEFAULT_PAGE_SIZE || '20'),
  PAGE_SIZE_OPTIONS: ['10', '20', '50', '100'],
  MAX_PAGE_SIZE: parseInt(import.meta.env.VITE_MAX_PAGE_SIZE || '100'),
  SHOW_SIZE_CHANGER: true,
  SHOW_QUICK_JUMPER: true,
} as const;

// 上传配置
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: parseInt(import.meta.env.VITE_MAX_FILE_SIZE || '10485760'), // 10MB
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  ALLOWED_DOCUMENT_TYPES: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
  ],
} as const;

// 主题配置
export const THEME_CONFIG = {
  PRIMARY_COLOR: import.meta.env.VITE_THEME_PRIMARY_COLOR || '#1890ff',
  BORDER_RADIUS: 6,
  LAYOUT: {
    HEADER_HEIGHT: 64,
    SIDEBAR_WIDTH: 240,
    SIDEBAR_COLLAPSED_WIDTH: 80,
    FOOTER_HEIGHT: 48,
  },
} as const;

// 表格配置
export const TABLE_CONFIG = {
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: ['10', '20', '50', '100'],
  SCROLL: { x: 'max-content' },
  SIZE: 'middle' as const,
  BORDERED: false,
  ROW_SELECTION_TYPE: 'checkbox' as const,
} as const;

// 表单配置
export const FORM_CONFIG = {
  LAYOUT: 'vertical' as const,
  LABEL_COL: { span: 24 },
  WRAPPER_COL: { span: 24 },
  SIZE: 'large' as const,
  VALIDATE_TRIGGER: ['onBlur', 'onChange'] as const,
} as const;

// 验证规则
export const VALIDATION_RULES = {
  EMAIL: {
    type: 'email' as const,
    message: '请输入有效的邮箱地址',
  },
  REQUIRED: {
    required: true,
    message: '此字段为必填项',
  },
  PASSWORD: {
    min: 8,
    max: 128,
    message: '密码长度必须在8-128个字符之间',
  },
  PHONE: {
    pattern: /^1[3-9]\d{9}$/,
    message: '请输入有效的手机号码',
  },
  URL: {
    type: 'url' as const,
    message: '请输入有效的URL地址',
  },
} as const;

// 状态配置
export const STATUS_CONFIG = {
  ACTIVE: { color: 'green', text: '启用' },
  INACTIVE: { color: 'red', text: '禁用' },
  PENDING: { color: 'orange', text: '待审核' },
  DISABLED: { color: 'gray', text: '已禁用' },
} as const;

// 角色配置
export const ROLE_CONFIG = {
  ADMIN: { color: 'red', text: '管理员' },
  USER: { color: 'blue', text: '用户' },
  VIEWER: { color: 'gray', text: '观察者' },
} as const;

// 供应商配置
export const SUPPLIER_CONFIG = {
  OPENAI: { name: 'OpenAI', icon: '🤖', color: '#10A37F' },
  ANTHROPIC: { name: 'Anthropic', icon: '🧠', color: '#D97706' },
  GOOGLE: { name: 'Google', icon: '🌈', color: '#4285F4' },
  AZURE: { name: 'Azure OpenAI', icon: '☁️', color: '#0078D4' },
  BAIDU: { name: '百度', icon: '🐻', color: '#3385FF' },
  ALIBABA: { name: '阿里云', icon: '☁️', color: '#FF6A00' },
} as const;

// 错误代码映射
export const ERROR_CODES = {
  // 认证错误
  '2001': '用户未认证，请先登录',
  '2002': '登录已过期，请重新登录',
  '2003': '令牌无效，请重新登录',
  '2004': '权限不足',
  '2005': '账户被锁定',
  '2006': '密码错误',
  
  // 业务逻辑错误
  '3001': '租户不存在',
  '3002': '用户已存在',
  '3003': '用户不存在',
  '3004': '凭证无效',
  '3005': '资源冲突',
  '3006': '操作不被允许',
  
  // 外部服务错误
  '4001': 'AI供应商服务错误',
  '4002': '记忆服务不可用',
  '4003': '外部API超时',
  '4004': '第三方服务错误',
  '4005': '网络错误',
  
  // 系统错误
  '5001': '数据库错误',
  '5002': '缓存错误',
  '5003': '内部服务器错误',
  '5004': '服务不可用',
  '5005': '配置错误',
} as const;

// 时间格式
export const DATE_FORMATS = {
  DATE: 'YYYY-MM-DD',
  TIME: 'HH:mm:ss',
  DATETIME: 'YYYY-MM-DD HH:mm:ss',
  DISPLAY_DATE: 'YYYY年MM月DD日',
  DISPLAY_DATETIME: 'YYYY年MM月DD日 HH:mm',
  RELATIVE: 'relative', // 相对时间显示
} as const;

// 动画配置
export const ANIMATION_CONFIG = {
  DURATION: {
    FAST: 200,
    NORMAL: 300,
    SLOW: 500,
  },
  EASING: 'cubic-bezier(0.25, 0.8, 0.25, 1)',
} as const;