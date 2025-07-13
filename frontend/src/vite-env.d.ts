/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_JWT_STORAGE_KEY: string
  readonly VITE_REFRESH_TOKEN_KEY: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
  readonly VITE_DEBUG_MODE: string
  readonly VITE_ENABLE_ANALYTICS: string
  readonly VITE_ANALYTICS_TRACKING_ID: string
  readonly VITE_SENTRY_DSN: string
  readonly VITE_OPENAI_API_KEY: string
  readonly VITE_ANTHROPIC_API_KEY: string
  readonly VITE_GOOGLE_API_KEY: string
  readonly VITE_MEMORY_ENABLED: string
  readonly VITE_FEATURE_USER_EXPORT: string
  readonly VITE_FEATURE_DARK_MODE: string
  readonly VITE_FEATURE_CHAT_EXPORT: string
  readonly VITE_FEATURE_VOICE_INPUT: string
  readonly VITE_FEATURE_IMAGE_UPLOAD: string
  readonly VITE_MAX_FILE_SIZE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}