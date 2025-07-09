/**
 * Lyss AI Platform - 路由保护组件
 * 功能描述: 保护需要认证和权限的路由
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import { Navigate } from 'react-router-dom'
import { Result, Spin } from 'antd'
import { useAuth, usePermissions } from '@/hooks/useAuth'

interface ProtectedRouteProps {
  children: React.ReactNode
  roles?: string[] // 需要的角色
  permissions?: string[] // 需要的权限
  requireAll?: boolean // 是否需要所有角色/权限，默认false（任一即可）
}

/**
 * 路由保护组件
 * 用于保护需要认证和特定权限的路由
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  roles = [],
  permissions = [],
  requireAll = false
}) => {
  const { isAuthenticated, isLoading, user } = useAuth()
  const { hasAnyRole, hasAllRoles } = usePermissions()

  // 加载中状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spin size="large" tip="验证用户权限中..." />
      </div>
    )
  }

  // 未认证，跳转到登录页
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // 检查角色权限
  if (roles.length > 0) {
    const hasRequiredRoles = requireAll ? hasAllRoles(roles) : hasAnyRole(roles)
    
    if (!hasRequiredRoles) {
      return (
        <Result
          status="403"
          title="权限不足"
          subTitle="抱歉，您没有访问此页面的权限。请联系管理员获取相应权限。"
          extra={
            <div className="text-sm text-gray-500 mt-4">
              <p>当前用户: {user?.email}</p>
              <p>用户角色: {user?.roles?.join(', ') || '无'}</p>
              <p>需要角色: {roles.join(requireAll ? ' 和 ' : ' 或 ')}</p>
            </div>
          }
        />
      )
    }
  }

  // TODO: 后续可以添加更细粒度的权限检查
  if (permissions.length > 0) {
    // 这里可以实现具体的权限检查逻辑
    // 目前先简单通过，后续可以扩展
  }

  // 用户状态检查
  if (user?.status === 'suspended') {
    return (
      <Result
        status="warning"
        title="账户已暂停"
        subTitle="您的账户已被暂停使用，请联系管理员了解详情。"
        extra={
          <div className="text-sm text-gray-500 mt-4">
            <p>如有疑问，请发送邮件至: support@lyss.ai</p>
          </div>
        }
      />
    )
  }

  if (user?.status === 'inactive') {
    return (
      <Result
        status="info"
        title="账户未激活"
        subTitle="您的账户尚未激活，请检查邮箱激活账户。"
        extra={
          <div className="text-sm text-gray-500 mt-4">
            <p>没有收到激活邮件? 请联系管理员</p>
          </div>
        }
      />
    )
  }

  // 通过所有检查，渲染子组件
  return <>{children}</>
}

export default ProtectedRoute