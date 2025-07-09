/**
 * Lyss AI Platform - 认证钩子
 * 功能描述: 认证相关的React钩子
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import { useEffect } from 'react'
import { useAuth as useAuthStore } from '@/stores/auth'

/**
 * 认证钩子 - 提供认证状态和方法
 */
export const useAuth = () => {
  const authStore = useAuthStore()

  // 组件挂载时检查认证状态
  useEffect(() => {
    const checkAuthStatus = async () => {
      // 如果有token但未认证，尝试验证
      const token = localStorage.getItem('access_token')
      if (token && !authStore.isAuthenticated) {
        authStore.setLoading(true)
        await authStore.checkAuth()
        authStore.setLoading(false)
      }
    }

    checkAuthStatus()
  }, [])

  return authStore
}

/**
 * 权限检查钩子
 */
export const usePermissions = () => {
  const { user } = useAuth()

  const hasRole = (role: string): boolean => {
    return user?.roles?.includes(role) || false
  }

  const hasAnyRole = (roles: string[]): boolean => {
    if (!user?.roles) return false
    return roles.some(role => user.roles.includes(role))
  }

  const hasAllRoles = (roles: string[]): boolean => {
    if (!user?.roles) return false
    return roles.every(role => user.roles.includes(role))
  }

  const isAdmin = (): boolean => {
    return hasAnyRole(['super_admin', 'tenant_admin'])
  }

  const isSuperAdmin = (): boolean => {
    return hasRole('super_admin')
  }

  const isTenantAdmin = (): boolean => {
    return hasRole('tenant_admin')
  }

  return {
    hasRole,
    hasAnyRole,
    hasAllRoles,
    isAdmin,
    isSuperAdmin,
    isTenantAdmin
  }
}

export default useAuth