/**
 * 主应用组件
 * 根据docs/frontend.md规范配置Ant Design主题和路由
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import relativeTime from 'dayjs/plugin/relativeTime';

// 页面组件
import LoginPage from '@/pages/login';
import DashboardPage from '@/pages/dashboard';
import ChatPage from '@/pages/chat';
import AdminLayout from '@/components/layout/AdminLayout';

// 管理页面
import TenantsPage from '@/pages/admin/tenants';
import UsersPage from '@/pages/admin/users';
import SuppliersPage from '@/pages/admin/suppliers';

// 通用组件
import ProtectedRoute from '@/components/common/ProtectedRoute';

// 错误页面
import NotFoundPage from '@/pages/error/NotFoundPage';
import UnauthorizedPage from '@/pages/error/UnauthorizedPage';
import ForbiddenPage from '@/pages/error/ForbiddenPage';

// 样式和配置
import { ROUTES, THEME_CONFIG } from '@/utils/constants';
import '@/styles/globals.css';

// 配置dayjs
dayjs.locale('zh-cn');
dayjs.extend(relativeTime);

// Ant Design主题配置
const antdTheme = {
  token: {
    colorPrimary: THEME_CONFIG.PRIMARY_COLOR,
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    borderRadius: THEME_CONFIG.BORDER_RADIUS,
    
    // 字体配置
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif',
    fontSize: 14,
    lineHeight: 1.5714285714285714,
    
    // 布局配置
    controlHeight: 32,
    controlHeightLG: 40,
    controlHeightSM: 24,
  },
  components: {
    Button: {
      borderRadius: 4,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
    },
    Input: {
      borderRadius: 4,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
    },
    Select: {
      borderRadius: 4,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
    },
    Table: {
      borderRadius: 8,
      headerBg: '#fafafa',
    },
    Card: {
      borderRadius: 8,
    },
    Layout: {
      headerBg: '#fff',
      siderBg: '#001529',
      bodyBg: '#f0f2f5',
    },
    Menu: {
      darkItemBg: '#001529',
      darkSubMenuItemBg: '#000c17',
    },
  },
  algorithm: undefined, // 使用默认算法
};

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={antdTheme}
      locale={zhCN}
      componentSize="middle"
    >
      <AntApp>
        <Router>
            <Routes>
              {/* 公共路由 */}
              <Route path={ROUTES.LOGIN} element={<LoginPage />} />
              
              {/* 错误页面 */}
              <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
              <Route path={ROUTES.UNAUTHORIZED} element={<UnauthorizedPage />} />
              <Route path={ROUTES.FORBIDDEN} element={<ForbiddenPage />} />
              
              {/* 管理员路由 */}
              <Route 
                path="/admin" 
                element={
                  <ProtectedRoute requiredRole="admin">
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route path="tenants" element={<TenantsPage />} />
                <Route path="users" element={<UsersPage />} />
                <Route path="suppliers" element={<SuppliersPage />} />
                <Route index element={<Navigate to="/admin/tenants" replace />} />
              </Route>
              
              {/* 用户功能路由 */}
              <Route 
                path="/dashboard" 
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<DashboardPage />} />
              </Route>
              
              <Route 
                path="/chat" 
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<ChatPage />} />
              </Route>
              
              <Route 
                path="/conversations" 
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>对话历史页面（待实现）</div>} />
              </Route>
              
              <Route 
                path="/memory" 
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>记忆管理页面（待实现）</div>} />
              </Route>
              
              <Route 
                path="/profile" 
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>个人中心页面（待实现）</div>} />
              </Route>
              
              <Route 
                path="/settings" 
                element={
                  <ProtectedRoute>
                    <AdminLayout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>设置页面（待实现）</div>} />
              </Route>
              
              {/* 根路径重定向 */}
              <Route 
                path="/" 
                element={<Navigate to={ROUTES.DASHBOARD} replace />} 
              />
              
              {/* 404页面 - 必须放在最后 */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Router>
        </AntApp>
      </ConfigProvider>
  );
};

export default App;