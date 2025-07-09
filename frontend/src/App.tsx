/**
 * Lyss AI Platform - 主应用组件
 * 功能描述: 应用的根组件，处理路由和认证
 * 作者: Claude AI Assistant
 * 创建时间: 2025-07-09
 * 最后更新: 2025-07-09
 */

import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'

import { useAuth } from '@/hooks/useAuth'
import LoginPage from '@/pages/auth/LoginPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import ConversationsPage from '@/pages/conversations/ConversationsPage'
import AdminPage from '@/pages/admin/AdminPage'
import SettingsPage from '@/pages/settings/SettingsPage'
import NotFoundPage from '@/pages/NotFoundPage'
import LoadingPage from '@/pages/LoadingPage'
import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'

// Ant Design主题配置
const themeConfig = {
  token: {
    colorPrimary: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1677ff',
    borderRadius: 6,
    fontSize: 14,
  },
  components: {
    Layout: {
      siderBg: '#ffffff',
      headerBg: '#ffffff',
    },
    Menu: {
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
    },
  },
}

function App() {
  const { isLoading, isAuthenticated } = useAuth()

  // 加载中状态
  if (isLoading) {
    return <LoadingPage />
  }

  return (
    <ConfigProvider 
      theme={themeConfig} 
      locale={zhCN}
    >
      <AntdApp>
        <div className="app min-h-screen">
          <Routes>
            {/* 公开路由 */}
            <Route 
              path="/login" 
              element={
                isAuthenticated ? (
                  <Navigate to="/dashboard" replace />
                ) : (
                  <LoginPage />
                )
              } 
            />

            {/* 受保护的路由 */}
            <Route 
              path="/*" 
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <Routes>
                      <Route path="/" element={<Navigate to="/dashboard" replace />} />
                      <Route path="/dashboard" element={<DashboardPage />} />
                      <Route path="/conversations/*" element={<ConversationsPage />} />
                      <Route 
                        path="/admin/*" 
                        element={
                          <ProtectedRoute roles={['super_admin', 'tenant_admin']}>
                            <AdminPage />
                          </ProtectedRoute>
                        } 
                      />
                      <Route path="/settings" element={<SettingsPage />} />
                      <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                  </MainLayout>
                </ProtectedRoute>
              } 
            />
          </Routes>
        </div>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App