/**
 * 主布局组件
 * 根据用户认证状态选择不同的布局
 */

import React from 'react';
import { useAuth } from '@/store/auth';
import AdminLayout from './AdminLayout';
// import GuestLayout from './GuestLayout'; // 如果需要访客布局

const MainLayout: React.FC = () => {
  const { isAuthenticated } = useAuth();

  // 根据认证状态返回不同的布局
  if (isAuthenticated) {
    return <AdminLayout />;
  }

  // 未认证用户（登录页面等）不需要布局
  return null;
};

export default MainLayout;