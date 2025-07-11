/**
 * 认证状态管理
 * 使用Zustand进行状态管理，根据docs/frontend.md规范
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AuthService } from '@/services/auth';
import { User, LoginCredentials, UserSession } from '@/types/user';
import { AuthAPI } from '@/types/api';

// 认证状态接口
interface AuthState {
  // 状态数据
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  
  // 认证操作
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  clearError: () => void;
  
  // 令牌管理
  setTokens: (accessToken: string, refreshToken: string) => void;
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  clearTokens: () => void;
  
  // 权限检查
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  
  // 租户信息
  getTenantId: () => string | null;
  getTenantInfo: () => { id: string; name: string; slug: string } | null;
}

// 存储键名
const JWT_STORAGE_KEY = import.meta.env.VITE_JWT_STORAGE_KEY || 'lyss_access_token';
const REFRESH_TOKEN_KEY = import.meta.env.VITE_REFRESH_TOKEN_KEY || 'lyss_refresh_token';

// 创建认证存储
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      /**
       * 用户登录
       */
      login: async (credentials: LoginCredentials) => {
        set({ loading: true, error: null });

        try {
          const response = await AuthService.login(credentials);
          const { user, access_token, refresh_token } = response.data!;

          // 存储令牌
          localStorage.setItem(JWT_STORAGE_KEY, access_token);
          localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);

          // 更新状态
          set({
            user,
            isAuthenticated: true,
            loading: false,
            error: null,
          });

          // 检查是否有重定向路径
          const redirectPath = sessionStorage.getItem('redirect_after_login');
          if (redirectPath) {
            sessionStorage.removeItem('redirect_after_login');
            window.location.href = redirectPath;
          } else {
            window.location.href = '/dashboard';
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : '登录失败';
          set({
            loading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          throw error;
        }
      },

      /**
       * 用户登出
       */
      logout: async () => {
        set({ loading: true });

        try {
          const refreshToken = get().getRefreshToken();
          
          // 调用后端登出API
          if (refreshToken) {
            await AuthService.logout(refreshToken);
          }
        } catch (error) {
          console.warn('登出API调用失败:', error);
          // 即使API调用失败，也要清除本地状态
        } finally {
          // 清除所有认证信息
          get().clearTokens();
          
          set({
            user: null,
            isAuthenticated: false,
            loading: false,
            error: null,
          });

          // 重定向到登录页
          window.location.href = '/login';
        }
      },

      /**
       * 刷新访问令牌
       */
      refreshToken: async () => {
        const refreshToken = get().getRefreshToken();
        
        if (!refreshToken) {
          throw new Error('无刷新令牌');
        }

        try {
          const response = await AuthService.refreshToken(refreshToken);
          const { access_token } = response.data!;
          
          // 更新访问令牌
          localStorage.setItem(JWT_STORAGE_KEY, access_token);
        } catch (error) {
          // 刷新失败，清除认证状态
          get().clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            error: '认证已过期，请重新登录',
          });
          
          throw error;
        }
      },

      /**
       * 获取当前用户信息
       */
      getCurrentUser: async () => {
        set({ loading: true, error: null });

        try {
          const response = await AuthService.getCurrentUser();
          const user = response.data!;

          set({
            user,
            isAuthenticated: true,
            loading: false,
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : '获取用户信息失败';
          set({
            loading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          throw error;
        }
      },

      /**
       * 清除错误状态
       */
      clearError: () => {
        set({ error: null });
      },

      /**
       * 设置认证令牌
       */
      setTokens: (accessToken: string, refreshToken: string) => {
        localStorage.setItem(JWT_STORAGE_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      },

      /**
       * 获取访问令牌
       */
      getAccessToken: () => {
        return localStorage.getItem(JWT_STORAGE_KEY);
      },

      /**
       * 获取刷新令牌
       */
      getRefreshToken: () => {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
      },

      /**
       * 清除所有令牌
       */
      clearTokens: () => {
        localStorage.removeItem(JWT_STORAGE_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      },

      /**
       * 检查用户是否有特定权限
       */
      hasPermission: (permission: string) => {
        const { user } = get();
        if (!user) return false;

        // 管理员拥有所有权限
        if (user.role === 'admin') return true;

        // TODO: 实现更复杂的权限检查逻辑
        // 当前简化版本，基于角色进行基本检查
        return false;
      },

      /**
       * 检查用户是否有特定角色
       */
      hasRole: (role: string) => {
        const { user } = get();
        return user?.role === role;
      },

      /**
       * 获取当前租户ID
       */
      getTenantId: () => {
        const { user } = get();
        return user?.tenant_id || null;
      },

      /**
       * 获取租户信息（简化版）
       */
      getTenantInfo: () => {
        const { user } = get();
        if (!user?.tenant_id) return null;

        // TODO: 从完整的租户信息中获取
        return {
          id: user.tenant_id,
          name: '当前租户', // 简化版本
          slug: 'current',
        };
      },
    }),
    {
      name: 'auth-storage',
      // 只持久化部分状态
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      // 版本控制
      version: 1,
      // 迁移函数
      migrate: (persistedState: any, version: number) => {
        if (version === 0) {
          // 从版本0迁移到版本1的逻辑
          return persistedState;
        }
        return persistedState;
      },
    }
  )
);

/**
 * 认证状态选择器
 */
export const authSelectors = {
  // 获取用户信息
  getUser: () => useAuthStore.getState().user,
  
  // 检查是否已认证
  isAuthenticated: () => useAuthStore.getState().isAuthenticated,
  
  // 检查是否为管理员
  isAdmin: () => useAuthStore.getState().user?.role === 'admin',
  
  // 获取用户角色
  getUserRole: () => useAuthStore.getState().user?.role,
  
  // 获取租户ID
  getTenantId: () => useAuthStore.getState().user?.tenant_id,
  
  // 检查加载状态
  isLoading: () => useAuthStore.getState().loading,
  
  // 获取错误信息
  getError: () => useAuthStore.getState().error,
};

/**
 * 认证状态Hook（便于在组件中使用）
 */
export const useAuth = () => {
  const store = useAuthStore();
  
  return {
    // 状态
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    loading: store.loading,
    error: store.error,
    
    // 操作
    login: store.login,
    logout: store.logout,
    getCurrentUser: store.getCurrentUser,
    clearError: store.clearError,
    
    // 权限检查
    hasPermission: store.hasPermission,
    hasRole: store.hasRole,
    isAdmin: store.user?.role === 'admin',
    
    // 租户信息
    tenantId: store.getTenantId(),
    tenantInfo: store.getTenantInfo(),
  };
};