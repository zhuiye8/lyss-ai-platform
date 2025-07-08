import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'

import { useAuth } from '@hooks/useAuth'
import LoginPage from '@pages/auth/LoginPage'
import DashboardPage from '@pages/dashboard/DashboardPage'
import ConversationsPage from '@pages/conversations/ConversationsPage'
import AdminPage from '@pages/admin/AdminPage'
import SettingsPage from '@pages/settings/SettingsPage'
import NotFoundPage from '@pages/NotFoundPage'
import LoadingPage from '@pages/LoadingPage'
import MainLayout from '@components/layout/MainLayout'
import ProtectedRoute from '@components/auth/ProtectedRoute'

import './App.css'

const { Content } = Layout

function App() {
  const { user, isLoading, isAuthenticated } = useAuth()

  if (isLoading) {
    return <LoadingPage />
  }

  return (
    <div className="app">
      <Routes>
        {/* Public routes */}
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

        {/* Protected routes */}
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
  )
}

export default App