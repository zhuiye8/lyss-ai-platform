/**
 * Lyss AI Platform - 认证状态管理
 * 功能描述: 用户认证和授权状态管理
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User, LoginRequest, LoginResponse } from '@/types'
import { post } from '@/utils/request'
import { message } from 'antd'

interface AuthState {
  // 状态
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  
  // 动作
  login: (credentials: LoginRequest) => Promise<boolean>
  logout: () => void
  refreshTokens: () => Promise<boolean>
  updateUser: (user: Partial<User>) => void
  checkAuth: () => Promise<boolean>
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      // 登录
      login: async (credentials: LoginRequest) => {
        set({ isLoading: true })
        
        try {
          const response = await post<LoginResponse>('/api/v1/auth/login', credentials)
          const { data } = response.data
          
          // 更新状态
          set({
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false
          })

          // 存储到localStorage（供请求拦截器使用）
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          localStorage.setItem('tenant_id', data.user.tenant_id)
          localStorage.setItem('user_info', JSON.stringify(data.user))

          message.success('登录成功')
          return true
        } catch (error) {
          console.error('登录失败:', error)
          set({ isLoading: false })
          return false
        }
      },

      // 登出
      logout: () => {
        // 调用后端登出接口
        post('/api/v1/auth/logout').catch(console.error)

        // 清除状态
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false
        })

        // 清除localStorage
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('tenant_id')
        localStorage.removeItem('user_info')

        message.success('已退出登录')
        
        // 跳转到登录页
        window.location.href = '/login'
      },

      // 刷新token
      refreshTokens: async () => {
        const { refreshToken } = get()
        
        if (!refreshToken) {
          return false
        }

        try {
          const response = await post<LoginResponse>('/api/v1/auth/refresh', {
            refresh_token: refreshToken
          })
          const { data } = response.data

          // 更新状态
          set({
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true
          })

          // 更新localStorage
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          localStorage.setItem('user_info', JSON.stringify(data.user))

          return true
        } catch (error) {
          console.error('刷新token失败:', error)
          // 刷新失败，执行登出
          get().logout()
          return false
        }
      },

      // 更新用户信息
      updateUser: (userData: Partial<User>) => {
        const { user } = get()
        if (user) {
          const updatedUser = { ...user, ...userData }
          set({ user: updatedUser })
          localStorage.setItem('user_info', JSON.stringify(updatedUser))
        }
      },

      // 检查认证状态
      checkAuth: async () => {
        const { accessToken, refreshToken } = get()
        
        if (!accessToken) {
          return false
        }

        try {
          // 验证当前token是否有效
          const response = await post('/api/v1/auth/verify')
          
          if (response.data.success) {
            return true
          } else {
            // token无效，尝试刷新
            return await get().refreshTokens()
          }
        } catch (error) {
          console.error('验证认证状态失败:', error)
          
          // 如果有refresh token，尝试刷新
          if (refreshToken) {
            return await get().refreshTokens()
          }
          
          // 都失败了，执行登出
          get().logout()
          return false
        }
      },

      // 设置加载状态
      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      }
    }),
    {
      name: 'auth-storage', // 存储key
      storage: createJSONStorage(() => sessionStorage), // 使用sessionStorage
      partialize: (state) => ({
        // 只持久化部分状态
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

// 导出钩子
export const useAuth = () => {
  const authState = useAuthStore()
  
  return {
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    login: authState.login,
    logout: authState.logout,
    updateUser: authState.updateUser,
    checkAuth: authState.checkAuth,
    refreshTokens: authState.refreshTokens,
    setLoading: authState.setLoading
  }
}