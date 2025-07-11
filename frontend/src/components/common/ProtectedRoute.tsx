/**
 * 路由守卫组件
 * 根据docs/frontend.md规范实现JWT认证和权限控制
 */

import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import { useAuth } from '@/store/auth';
import { ROUTES } from '@/utils/constants';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
  requiredPermission?: string;
  fallbackPath?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
  fallbackPath = ROUTES.LOGIN,
}) => {
  const {
    isAuthenticated,
    loading,
    user,
    getCurrentUser,
    hasRole,
    hasPermission,
  } = useAuth();
  const location = useLocation();

  // 组件挂载时获取用户信息
  useEffect(() => {
    if (isAuthenticated && !user && !loading) {
      getCurrentUser().catch((error) => {
        console.error('获取用户信息失败:', error);
      });
    }
  }, [isAuthenticated, user, loading, getCurrentUser]);

  // 显示加载状态
  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
        }}
      >
        <Spin size="large" />
        <div style={{ marginTop: 16, color: '#666' }}>
          正在验证身份...
        </div>
      </div>
    );
  }

  // 未认证，重定向到登录页
  if (!isAuthenticated) {
    // 保存当前路径，登录后跳转回来
    if (location.pathname !== ROUTES.LOGIN) {
      sessionStorage.setItem('redirect_after_login', location.pathname + location.search);
    }
    
    return <Navigate to={fallbackPath} replace />;
  }

  // 已认证但用户信息缺失
  if (!user) {
    return (
      <Result
        status="warning"
        title="用户信息获取失败"
        subTitle="无法获取用户信息，请尝试重新登录"
        extra={
          <Button type="primary" onClick={() => window.location.href = ROUTES.LOGIN}>
            重新登录
          </Button>
        }
      />
    );
  }

  // 检查角色权限
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <Navigate 
        to={ROUTES.UNAUTHORIZED} 
        state={{ 
          from: location,
          reason: `需要${requiredRole}角色权限` 
        }} 
        replace 
      />
    );
  }

  // 检查具体权限
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <Navigate 
        to={ROUTES.FORBIDDEN} 
        state={{ 
          from: location,
          reason: `缺少${requiredPermission}权限` 
        }} 
        replace 
      />
    );
  }

  // 权限验证通过，渲染子组件
  return <>{children}</>;
};

export default ProtectedRoute;