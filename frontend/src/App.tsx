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
import Layout from '@/components/layout/Layout';

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

// 现代化主题配色方案
const antdTheme = {
  token: {
    // 主色调 - 使用更现代的蓝色
    colorPrimary: '#2563eb', // Tailwind blue-600
    colorSuccess: '#16a34a', // Tailwind green-600  
    colorWarning: '#d97706', // Tailwind amber-600
    colorError: '#dc2626',   // Tailwind red-600
    colorInfo: '#0ea5e9',    // Tailwind sky-500
    
    // 中性色调
    colorTextBase: '#1f2937',      // Tailwind gray-800
    colorText: '#374151',          // Tailwind gray-700
    colorTextSecondary: '#6b7280', // Tailwind gray-500
    colorTextTertiary: '#9ca3af',  // Tailwind gray-400
    colorTextQuaternary: '#d1d5db', // Tailwind gray-300
    
    // 背景色
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBgLayout: '#f8fafc',      // Tailwind slate-50
    colorBgSpotlight: '#f1f5f9',   // Tailwind slate-100
    colorBgMask: 'rgba(0, 0, 0, 0.45)',
    
    // 边框和分割线
    colorBorder: '#e2e8f0',        // Tailwind slate-200
    colorBorderSecondary: '#f1f5f9', // Tailwind slate-100
    colorSplit: '#f1f5f9',
    
    // 字体配置
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "SF Pro Display", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    fontSize: 14,
    fontSizeSM: 12,
    fontSizeLG: 16,
    fontSizeXL: 20,
    fontSizeHeading1: 38,
    fontSizeHeading2: 30,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 16,
    lineHeight: 1.5714,
    lineHeightSM: 1.66,
    lineHeightLG: 1.5,
    
    // 控件尺寸
    controlHeight: 36,
    controlHeightLG: 44,
    controlHeightSM: 28,
    controlHeightXS: 24,
    
    // 圆角配置 - 更现代的圆角
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 6,
    borderRadiusXS: 4,
    
    // 阴影配置 - 更精致的阴影
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
    boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
    boxShadowTertiary: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
    
    // 动画配置
    motionDurationFast: '0.1s',
    motionDurationMid: '0.2s',
    motionDurationSlow: '0.3s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    motionEaseOutBack: 'cubic-bezier(0.12, 0.4, 0.29, 1.46)',
    motionEaseInBack: 'cubic-bezier(0.71, -0.46, 0.88, 0.6)',
    motionEaseInQuint: 'cubic-bezier(0.755, 0.05, 0.855, 0.06)',
    motionEaseOutQuint: 'cubic-bezier(0.23, 1, 0.32, 1)',
  },
  components: {
    Layout: {
      // 现代化布局配色
      headerBg: '#ffffff',
      headerHeight: 64,
      headerPadding: '0 24px',
      siderBg: '#ffffff',       // 改为白色背景
      bodyBg: '#f8fafc',        // 浅灰背景
      footerBg: '#ffffff',
      footerPadding: '24px 48px',
      zeroTriggerWidth: 42,
      zeroTriggerHeight: 42,
      lightSiderBg: '#ffffff',
      lightTriggerBg: '#ffffff',
      lightTriggerColor: '#1f2937',
    },
    Menu: {
      // 菜单样式优化
      itemBg: 'transparent',
      itemColor: '#374151',           // 深灰色文字
      itemHoverBg: '#f1f5f9',         // 悬停背景
      itemHoverColor: '#1f2937',      // 悬停文字色
      itemSelectedBg: '#eff6ff',      // 选中背景 - 蓝色系
      itemSelectedColor: '#2563eb',    // 选中文字色
      itemActiveBg: '#dbeafe',        // 激活背景
      subMenuItemBg: 'transparent',
      groupTitleColor: '#6b7280',     // 分组标题色
      groupTitleLineHeight: '32px',
      iconSize: 16,
      iconMarginInlineEnd: 10,
      collapsedIconSize: 16,
      itemMarginBlock: 4,
      itemMarginInline: 4,
      itemPaddingInline: 12,
      horizontalItemBorderRadius: 8,
      horizontalItemHoverBg: '#f1f5f9',
      popupBg: '#ffffff',
      darkItemBg: '#1e293b',
      darkItemColor: '#e2e8f0',
      darkItemHoverBg: '#334155',
      darkItemHoverColor: '#f8fafc',
      darkItemSelectedBg: '#3730a3',
      darkItemSelectedColor: '#ffffff',
      darkSubMenuItemBg: '#1e293b',
      darkGroupTitleColor: '#94a3b8',
    },
    Button: {
      // 按钮样式现代化
      borderRadius: 8,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
      fontWeight: 500,
      primaryShadow: '0 2px 4px rgba(37, 99, 235, 0.2)',
      defaultShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
    },
    Input: {
      // 输入框样式优化
      borderRadius: 8,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
      paddingInline: 12,
      paddingInlineLG: 16,
      paddingInlineSM: 8,
    },
    Select: {
      borderRadius: 8,
      controlHeight: 36,
      controlHeightLG: 44,
      controlHeightSM: 28,
      selectorBg: '#ffffff',
      optionSelectedBg: '#eff6ff',
      optionActiveBg: '#f1f5f9',
    },
    Table: {
      borderRadius: 12,
      headerBg: '#f8fafc',
      headerColor: '#374151',
      headerSortActiveBg: '#f1f5f9',
      headerSortHoverBg: '#f1f5f9',
      bodySortBg: '#fafbfc',
      rowHoverBg: '#f8fafc',
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
      cellPaddingBlockMD: 8,
      cellPaddingInlineMD: 12,
      cellPaddingBlockSM: 6,
      cellPaddingInlineSM: 8,
    },
    Card: {
      borderRadius: 12,
      boxShadowTertiary: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
      headerBg: 'transparent',
      headerHeight: 48,
      headerHeightSM: 36,
      bodyPadding: 24,
      paddingLG: 32,
      paddingSM: 16,
    },
    Drawer: {
      borderRadius: 0,
      headerHeight: 56,
      bodyPadding: 24,
      footerPaddingBlock: 12,
      footerPaddingInline: 24,
    },
    Modal: {
      borderRadius: 12,
      headerBg: '#ffffff',
      headerHeight: 56,
      bodyPadding: 24,
      footerBg: '#f8fafc',
      footerBorderTop: '1px solid #e2e8f0',
    },
    Breadcrumb: {
      fontSize: 14,
      iconFontSize: 12,
      linkColor: '#6b7280',
      linkHoverColor: '#2563eb',
      itemColor: '#9ca3af',
      lastItemColor: '#1f2937',
      separatorColor: '#d1d5db',
      separatorMargin: 8,
    },
    Typography: {
      titleMarginTop: 0,
      titleMarginBottom: 16,
      fontFamilyCode: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", "Source Code Pro", "Consolas", monospace',
    },
    Divider: {
      colorSplit: '#e2e8f0',
      orientationMargin: 0.05,
      verticalMarginInline: 8,
    },
    Badge: {
      dotSize: 6,
      fontSize: 12,
      fontWeight: 500,
      statusSize: 6,
      textFontSize: 12,
      textFontSizeSM: 10,
      textFontWeight: 'normal',
    },
    Tooltip: {
      borderRadius: 6,
      colorBgSpotlight: 'rgba(0, 0, 0, 0.85)',
      colorTextLightSolid: '#ffffff',
    },
    Avatar: {
      borderRadius: 6,
      groupBorderColor: '#ffffff',
      groupOverlapOffset: -8,
      groupSpace: 4,
    },
  },
  algorithm: undefined, // 使用默认算法，保持明亮主题
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
                    <Layout />
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
                    <Layout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<DashboardPage />} />
              </Route>
              
              <Route 
                path="/chat" 
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<ChatPage />} />
              </Route>
              
              <Route 
                path="/conversations" 
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>对话历史页面（待实现）</div>} />
              </Route>
              
              <Route 
                path="/memory" 
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>记忆管理页面（待实现）</div>} />
              </Route>
              
              <Route 
                path="/profile" 
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                } 
              >
                <Route index element={<div>个人中心页面（待实现）</div>} />
              </Route>
              
              <Route 
                path="/settings" 
                element={
                  <ProtectedRoute>
                    <Layout />
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