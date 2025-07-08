/**
 * Common types and interfaces for the Lyss AI Platform
 */

// User and Authentication Types
export interface User {
  user_id: string
  tenant_id: string
  email: string
  username?: string
  first_name?: string
  last_name?: string
  profile_picture?: string
  status: 'active' | 'inactive' | 'suspended' | 'deleted'
  roles: string[]
  last_login_at?: string
  preferences: UserPreferences
  created_at: string
  updated_at: string
}

export interface UserPreferences {
  theme: 'light' | 'dark'
  language: string
  timezone: string
  notifications: {
    email: boolean
    push: boolean
    browser: boolean
  }
  ai_settings: {
    default_model: string
    temperature: number
    max_tokens: number
    use_memory: boolean
  }
}

export interface LoginRequest {
  email: string
  password: string
  remember_me?: boolean
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

// Tenant Types
export interface TenantConfig {
  max_users: number
  max_conversations_per_user: number
  max_api_calls_per_month: number
  max_storage_gb: number
  max_memory_entries: number
  enabled_models: string[]
  model_rate_limits: Record<string, number>
  features: Record<string, boolean>
  custom_branding: Record<string, any>
  webhook_endpoints: string[]
  ip_whitelist: string[]
}

export interface Tenant {
  tenant_id: string
  tenant_name: string
  tenant_slug: string
  contact_email: string
  contact_name?: string
  company_name?: string
  status: 'active' | 'suspended' | 'deleted' | 'trial'
  subscription_plan: 'free' | 'basic' | 'professional' | 'enterprise'
  config: TenantConfig
  created_at: string
  updated_at: string
}

// Conversation Types
export interface Conversation {
  conversation_id: string
  tenant_id: string
  user_id: string
  title: string
  summary?: string
  status: 'active' | 'archived' | 'deleted'
  metadata: Record<string, any>
  message_count: number
  last_message_at?: string
  created_at: string
  updated_at: string
}

export interface Message {
  message_id: string
  conversation_id: string
  tenant_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  content_type: string
  metadata: Record<string, any>
  attachments: MessageAttachment[]
  created_at: string
  updated_at: string
}

export interface MessageAttachment {
  type: 'file' | 'image' | 'link'
  url: string
  name: string
  size?: number
  mime_type?: string
}

export interface SendMessageRequest {
  content: string
  content_type?: string
  metadata?: Record<string, any>
  attachments?: MessageAttachment[]
}

// AI Provider Types
export interface AIProvider {
  credential_id: string
  tenant_id: string
  provider_name: string
  provider_type: string
  display_name: string
  status: 'active' | 'inactive'
  model_mappings: Record<string, AIModel>
  rate_limits: Record<string, number>
  last_used_at?: string
  created_at: string
  updated_at: string
}

export interface AIModel {
  model_name: string
  model_type: 'chat' | 'completion' | 'embedding'
  context_window: number
  max_tokens: number
  supports_streaming: boolean
  supports_function_calling: boolean
}

// Memory Types
export interface Memory {
  memory_id: string
  content: string
  relevance_score?: number
  category?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface MemorySearchRequest {
  query: string
  limit?: number
  threshold?: number
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message: string
  request_id?: string
  timestamp: string
  errors?: ApiError[]
}

export interface ApiError {
  code: string
  message: string
  field?: string
  details?: string
}

export interface PaginationMeta {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMeta
}

// Usage Statistics Types
export interface UsageStats {
  date: string
  total_api_calls: number
  total_tokens: number
  total_cost_usd: number
  unique_users: number
  provider_breakdown: Record<string, ProviderUsage>
}

export interface ProviderUsage {
  api_calls: number
  tokens: number
  cost_usd: number
}

export interface UsageStatsSummary {
  total_api_calls: number
  total_tokens: number
  total_cost_usd: number
  average_daily_calls: number
  most_used_provider: string
}

// Stream Types for real-time chat
export interface StreamMessage {
  type: 'message_start' | 'content_delta' | 'message_end' | 'error'
  message_id?: string
  delta?: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  error?: string
}

// Component Props Types
export interface ConversationListProps {
  conversations: Conversation[]
  selectedConversationId?: string
  onSelectConversation: (conversationId: string) => void
  onCreateConversation: () => void
}

export interface ChatInterfaceProps {
  conversation?: Conversation
  messages: Message[]
  onSendMessage: (message: SendMessageRequest) => void
  isLoading?: boolean
}

export interface MessageBubbleProps {
  message: Message
  isCurrentUser?: boolean
  showAvatar?: boolean
}

// Form Types
export interface CreateConversationForm {
  title: string
  metadata?: Record<string, any>
}

export interface UpdateUserForm {
  first_name?: string
  last_name?: string
  username?: string
  preferences?: Partial<UserPreferences>
}

export interface CreateAIProviderForm {
  provider_name: string
  provider_type: string
  display_name: string
  api_key: string
  base_url?: string
  model_mappings: Record<string, AIModel>
  rate_limits: Record<string, number>
}

// Route Types
export interface RouteConfig {
  path: string
  component: React.ComponentType
  exact?: boolean
  protected?: boolean
  roles?: string[]
  permissions?: string[]
}

// Theme Types
export interface ThemeConfig {
  token: {
    colorPrimary: string
    colorSuccess: string
    colorWarning: string
    colorError: string
    colorInfo: string
    colorBgBase: string
    colorTextBase: string
    borderRadius: number
    fontSize: number
  }
  components?: Record<string, any>
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'conversation_update' | 'message_received' | 'typing_indicator' | 'system_notification'
  conversation_id?: string
  message?: Message
  data?: any
}

// Error Types
export class ApiError extends Error {
  public status: number
  public code: string
  public details?: any

  constructor(message: string, status: number, code: string, details?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}